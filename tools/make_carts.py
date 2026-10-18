#!/usr/bin/env python3
"""make_carts.py - compiler for Arcadia expansion cartridges (.arc) + headless self-test.

    python make_carts.py                 compile tools/carts/*.arcl -> tools/out/carts/*.arc, then self-test them
    python make_carts.py --no-test       compile only
    python make_carts.py --test-only     self-test the existing .arc files
    python make_carts.py file.arcl ...   compile just these sources
    python make_carts.py --shots         also write a PPM/PNG-ish screenshot of every cart into tools/out/shots

The language ("ARCL") is a small C-like language, see README_CARTS.txt.  The VM and the file
format are specified by tools/arcvm_ref.py (the reference interpreter), which is also what the
self-test runs.
"""
import os, re, struct, sys, glob, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arcvm_ref as R

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(HERE, 'carts')
OUT_DIR = os.path.join(HERE, 'out', 'carts')


class CompileError(Exception):
    pass


# ----------------------------------------------------------------------------------------
# lexer
# ----------------------------------------------------------------------------------------
TOK_RE = re.compile(r'''
    (?P<ws>[ \t\r]+)
  | (?P<nl>\n)
  | (?P<cmt>//[^\n]*)
  | (?P<hex>0[xX][0-9a-fA-F]+)
  | (?P<num>\d+)
  | (?P<chr>'(?:\\.|[^'\\])')
  | (?P<str>"(?:\\.|[^"\\])*")
  | (?P<id>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<op><<=|>>=|==|!=|<=|>=|<<|>>|&&|\|\||\+=|-=|\*=|/=|%=|&=|\|=|\^=|\+\+|--|[-+*/%&|^~!<>=(){}\[\];,?:])
''', re.X)


def unescape(s):
    return s.encode('latin1').decode('unicode_escape')


def lex(src):
    toks = []
    pos, line = 0, 1
    while pos < len(src):
        m = TOK_RE.match(src, pos)
        if not m:
            raise CompileError('line %d: bad character %r' % (line, src[pos]))
        k = m.lastgroup
        t = m.group()
        pos = m.end()
        if k == 'nl':
            line += 1
        elif k in ('ws', 'cmt'):
            pass
        elif k == 'hex':
            toks.append(('num', int(t, 16), line))
        elif k == 'num':
            toks.append(('num', int(t), line))
        elif k == 'chr':
            toks.append(('num', ord(unescape(t[1:-1])), line))
        elif k == 'str':
            toks.append(('str', unescape(t[1:-1]), line))
        elif k == 'id':
            toks.append(('id', t, line))
        else:
            toks.append(('op', t, line))
    toks.append(('eof', '', line))
    return toks


# ----------------------------------------------------------------------------------------
# directives (@name ...) and meta
# ----------------------------------------------------------------------------------------
def split_directives(src):
    """Returns (code_text_with_blank_lines, [(lineno, name, [args])])."""
    out_lines = []
    dirs = []
    lines = src.split('\n')
    i = 0
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if s.startswith('@'):
            start = i
            text = s
            i += 1
            while i < len(lines) and lines[i].strip().startswith('"'):
                text += ' ' + lines[i].strip()
                out_lines.append('')
                i += 1
            out_lines.append('')
            # strip trailing comment
            text = re.sub(r'\s//.*$', '', text) if '"' not in text.split('//')[-1] else text
            m = re.match(r'@(\w+)\s*(.*)$', text)
            if not m:
                raise CompileError('line %d: bad directive' % (start + 1))
            rest = m.group(2)
            args = []
            for am in re.finditer(r'"((?:\\.|[^"\\])*)"|(\S+)', rest):
                if am.group(1) is not None:
                    args.append(('s', unescape(am.group(1))))
                else:
                    args.append(('w', am.group(2)))
            dirs.append((start + 1, m.group(1), args))
            continue
        out_lines.append(ln)
        i += 1
    return '\n'.join(out_lines), dirs


# ----------------------------------------------------------------------------------------
# parser
# ----------------------------------------------------------------------------------------
class P:
    def __init__(self, toks):
        self.t = toks
        self.i = 0

    def peek(self, k=0):
        return self.t[min(self.i + k, len(self.t) - 1)]

    def next(self):
        t = self.t[self.i]
        self.i += 1
        return t

    def err(self, msg, t=None):
        t = t or self.peek()
        raise CompileError('line %d: %s (near %r)' % (t[2], msg, t[1]))

    def is_op(self, v):
        t = self.peek()
        return t[0] == 'op' and t[1] == v

    def is_kw(self, v):
        t = self.peek()
        return t[0] == 'id' and t[1] == v

    def accept_op(self, v):
        if self.is_op(v):
            self.i += 1
            return True
        return False

    def expect_op(self, v):
        if not self.accept_op(v):
            self.err('expected %r' % v)

    def expect_id(self):
        t = self.next()
        if t[0] != 'id':
            self.err('expected a name', t)
        return t[1]

    # --- expressions (precedence climbing) ---
    BIN = [('||',), ('&&',), ('|',), ('^',), ('&',), ('==', '!='), ('<', '<=', '>', '>='), ('<<', '>>'),
           ('+', '-'), ('*', '/', '%')]

    def expr(self, lvl=-1):
        if lvl == -1:                       # ternary  c ? a : b  (lowest precedence)
            c = self.expr(0)
            if self.is_op('?'):
                t = self.next()
                a = self.expr(-1)
                self.expect_op(':')
                b = self.expr(-1)
                return ('tern', c, a, b, t[2])
            return c
        if lvl >= len(self.BIN):
            return self.unary()
        a = self.expr(lvl + 1)
        while True:
            t = self.peek()
            if t[0] == 'op' and t[1] in self.BIN[lvl]:
                self.i += 1
                b = self.expr(lvl + 1)
                a = ('bin', t[1], a, b, t[2])
            else:
                return a

    def unary(self):
        t = self.peek()
        if t[0] == 'op' and t[1] in ('-', '!', '~'):
            self.i += 1
            return ('un', t[1], self.unary(), t[2])
        return self.postfix()

    def postfix(self):
        t = self.next()
        if t[0] == 'num':
            return ('num', t[1], t[2])
        if t[0] == 'str':
            return ('str', t[1], t[2])
        if t[0] == 'op' and t[1] == '(':
            e = self.expr()
            self.expect_op(')')
            return e
        if t[0] == 'id':
            if self.is_op('('):
                self.i += 1
                args = []
                if not self.is_op(')'):
                    while True:
                        args.append(self.expr())
                        if not self.accept_op(','):
                            break
                self.expect_op(')')
                return ('call', t[1], args, t[2])
            if self.is_op('['):
                self.i += 1
                ix = self.expr()
                self.expect_op(']')
                return ('idx', t[1], ix, t[2])
            return ('name', t[1], t[2])
        self.err('expected an expression', t)

    # --- statements ---
    ASSIGN = ('=', '+=', '-=', '*=', '/=', '%=', '&=', '|=', '^=', '<<=', '>>=')

    def simple(self):
        e = self.expr()
        t = self.peek()
        if t[0] == 'op' and t[1] in self.ASSIGN:
            self.i += 1
            if e[0] not in ('name', 'idx'):
                self.err('cannot assign to this', t)
            rhs = self.expr()
            return ('assign', e, t[1], rhs, t[2])
        if t[0] == 'op' and t[1] in ('++', '--'):
            self.i += 1
            if e[0] not in ('name', 'idx'):
                self.err('cannot modify this', t)
            return ('assign', e, '+=' if t[1] == '++' else '-=', ('num', 1, t[2]), t[2])
        if e[0] != 'call':
            self.err('this expression does nothing', t)
        return ('expr', e, t[2])

    def vardecl(self):
        decls = []
        while True:
            t = self.next()
            if t[0] != 'id':
                self.err('expected a name', t)
            init = None
            if self.accept_op('='):
                init = self.expr()
            decls.append((t[1], init, t[2]))
            if not self.accept_op(','):
                break
        return decls

    def stmt(self):
        t = self.peek()
        if t[0] == 'op' and t[1] == '{':
            return self.block()
        if t[0] == 'id':
            k = t[1]
            if k == 'var':
                self.i += 1
                d = self.vardecl()
                self.expect_op(';')
                return ('vars', d, t[2])
            if k == 'if':
                self.i += 1
                self.expect_op('(')
                c = self.expr()
                self.expect_op(')')
                a = self.stmt()
                b = None
                if self.is_kw('else'):
                    self.i += 1
                    b = self.stmt()
                return ('if', c, a, b, t[2])
            if k == 'while':
                self.i += 1
                self.expect_op('(')
                c = self.expr()
                self.expect_op(')')
                return ('while', c, self.stmt(), t[2])
            if k == 'for':
                self.i += 1
                self.expect_op('(')
                init = None if self.is_op(';') else self.simple_or_var()
                self.expect_op(';')
                cond = None if self.is_op(';') else self.expr()
                self.expect_op(';')
                step = None if self.is_op(')') else self.simple()
                self.expect_op(')')
                return ('for', init, cond, step, self.stmt(), t[2])
            if k == 'break' or k == 'continue':
                self.i += 1
                self.expect_op(';')
                return (k, t[2])
            if k == 'return':
                self.i += 1
                e = None if self.is_op(';') else self.expr()
                self.expect_op(';')
                return ('return', e, t[2])
        s = self.simple()
        self.expect_op(';')
        return s

    def simple_or_var(self):
        if self.is_kw('var'):
            t = self.next()
            return ('vars', self.vardecl(), t[2])
        return self.simple()

    def block(self):
        self.expect_op('{')
        out = []
        while not self.is_op('}'):
            if self.peek()[0] == 'eof':
                self.err('missing }')
            out.append(self.stmt())
        self.expect_op('}')
        return ('block', out)

    def program(self):
        items = []
        while self.peek()[0] != 'eof':
            t = self.next()
            if t[0] != 'id':
                self.err('expected const/var/array/func', t)
            if t[1] == 'const':
                n = self.expect_id()
                self.expect_op('=')
                e = self.expr()
                self.expect_op(';')
                items.append(('const', n, e, t[2]))
            elif t[1] == 'var':
                items.append(('vars', self.vardecl(), t[2]))
                self.expect_op(';')
            elif t[1] == 'array':
                n = self.expect_id()
                self.expect_op('[')
                sz = self.expr()
                self.expect_op(']')
                init = None
                if self.accept_op('='):
                    self.expect_op('{')
                    init = []
                    if not self.is_op('}'):
                        while True:
                            init.append(self.expr())
                            if not self.accept_op(','):
                                break
                    self.expect_op('}')
                self.expect_op(';')
                items.append(('array', n, sz, init, t[2]))
            elif t[1] == 'func':
                n = self.expect_id()
                self.expect_op('(')
                params = []
                if not self.is_op(')'):
                    while True:
                        params.append(self.expect_id())
                        if not self.accept_op(','):
                            break
                self.expect_op(')')
                items.append(('func', n, params, self.block(), t[2]))
            else:
                self.err('expected const/var/array/func', t)
        return items


# ----------------------------------------------------------------------------------------
# code generation
# ----------------------------------------------------------------------------------------
BIN_OPS = {'+': 'ADD', '-': 'SUB', '*': 'MUL', '/': 'DIV', '%': 'MOD', '&': 'AND', '|': 'OR', '^': 'XOR',
           '<<': 'SHL', '>>': 'SHR', '==': 'EQ', '!=': 'NE', '<': 'LT', '<=': 'LE', '>': 'GT', '>=': 'GE'}


def w16(x):
    return R.w16(x)


class Gen:
    def __init__(self, items, consts):
        self.items = items
        self.consts = dict(consts)       # name -> int
        self.code = bytearray()
        self.strs = bytearray()
        self.str_ix = {}
        self.globals = {}
        self.arrays = {}                 # name -> (base, size)
        self.mem_init = []
        self.mem_words = 0
        self.funcs = {}                  # name -> dict(addr, nargs, nloc, node)
        self.fixups = []                 # (pos, funcname, line)
        self.loc = None
        self.loops = []
        self.line = 0

    def err(self, msg, line=None):
        raise CompileError('line %d: %s' % (line or self.line, msg))

    # --- constants ---
    def const_eval(self, e):
        k = e[0]
        if k == 'num':
            return e[1]
        if k == 'name':
            if e[1] in self.consts:
                return self.consts[e[1]]
            self.err('%r is not a constant' % e[1], e[2])
        if k == 'str':
            return self.string(e[1])
        if k == 'tern':
            return self.const_eval(e[2]) if self.const_eval(e[1]) else self.const_eval(e[3])
        if k == 'un':
            a = self.const_eval(e[2])
            return w16({'-': -a, '!': int(a == 0), '~': ~a}[e[1]])
        if k == 'bin':
            a, b = self.const_eval(e[2]), self.const_eval(e[3])
            o = e[1]
            if o in ('/', '%'):
                if b == 0:
                    self.err('divide by zero', e[4])
                q = abs(a) // abs(b) * (1 if (a < 0) == (b < 0) else -1)
                return w16(q if o == '/' else a - b * q)
            if o == '&&':
                return int(bool(a) and bool(b))
            if o == '||':
                return int(bool(a) or bool(b))
            f = {'+': lambda: a + b, '-': lambda: a - b, '*': lambda: a * b, '&': lambda: a & b, '|': lambda: a | b,
                 '^': lambda: a ^ b, '<<': lambda: a << (b & 15), '>>': lambda: a >> (b & 15),
                 '==': lambda: int(a == b), '!=': lambda: int(a != b), '<': lambda: int(a < b),
                 '<=': lambda: int(a <= b), '>': lambda: int(a > b), '>=': lambda: int(a >= b)}[o]
            return w16(f())
        self.err('not a constant expression')

    def string(self, s):
        if s in self.str_ix:
            return self.str_ix[s]
        b = s.encode('latin1')
        off = len(self.strs)
        if off + len(b) + 1 > R.STR_MAX:
            self.err('string pool too big')
        self.str_ix[s] = off
        self.strs += b + b'\0'
        return off

    # --- emit ---
    def op(self, name, *operands):
        self.code.append(R.CORE[name])
        for o in operands:
            self.code.append(o & 255)

    def push(self, v):
        v = w16(v)
        if -128 <= v <= 127:
            self.code += bytes((R.CORE['PUSH8'], v & 255))
        else:
            self.code += bytes((R.CORE['PUSH16'], v & 255, (v >> 8) & 255))

    def jump(self, name):
        self.code.append(R.CORE[name])
        pos = len(self.code)
        self.code += b'\0\0'
        return pos

    def patch(self, pos, target=None):
        t = len(self.code) if target is None else target
        self.code[pos] = t & 255
        self.code[pos + 1] = (t >> 8) & 255

    def jump_to(self, name, target):
        self.code.append(R.CORE[name])
        self.code += bytes((target & 255, (target >> 8) & 255))

    # --- program ---
    def build(self):
        # pass 1: globals, arrays, consts, function table
        gvars = []
        for it in self.items:
            self.line = it[-1] if isinstance(it[-1], int) else self.line
            if it[0] == 'const':
                self.consts[it[1]] = self.const_eval(it[2])
            elif it[0] == 'vars':
                for (n, init, ln) in it[1]:
                    if n in self.globals or n in self.consts:
                        self.err('%r already defined' % n, ln)
                    if len(self.globals) >= R.GLOBALS_MAX:
                        self.err('too many global variables (max %d)' % R.GLOBALS_MAX, ln)
                    self.globals[n] = len(self.globals)
                    if init is not None:
                        gvars.append((n, init))
            elif it[0] == 'array':
                n = it[1]
                sz = self.const_eval(it[2])
                if sz < 1 or self.mem_words + sz > R.MEM_MAX:
                    self.err('array %r too big (mem limit %d words)' % (n, R.MEM_MAX), it[4])
                if n in self.arrays or n in self.globals or n in self.consts:
                    self.err('%r already defined' % n, it[4])
                base = self.mem_words
                self.arrays[n] = (base, sz)
                self.mem_words += sz
                if it[3] is not None:
                    vals = [self.const_eval(e) for e in it[3]]
                    if len(vals) > sz:
                        self.err('too many initial values for %r' % n, it[4])
                    while len(self.mem_init) < base:
                        self.mem_init.append(0)
                    self.mem_init += vals
            elif it[0] == 'func':
                if it[1] in self.funcs or it[1] in R.BUILTINS:
                    self.err('function %r already defined / reserved' % it[1], it[4])
                self.funcs[it[1]] = dict(addr=None, nargs=len(it[2]), nloc=0, node=it)
        if 'frame' not in self.funcs:
            self.err('the cart needs a func frame()')
        if self.funcs['frame']['nargs'] != 0:
            self.err('frame() takes no arguments')
        if 'init' in self.funcs and self.funcs['init']['nargs'] != 0:
            self.err('init() takes no arguments')
        # entry stubs
        self.init_addr = len(self.code)
        self.loc = {}
        for (n, init) in gvars:
            self.expr(init)
            self.op('STG', self.globals[n])
        if 'init' in self.funcs:
            self.call_user('init', 0, 0)
            self.op('DROP')
        self.push(0)
        self.op('RET')
        self.frame_addr = len(self.code)
        self.call_user('frame', 0, 0)
        self.op('DROP')
        self.push(0)
        self.op('RET')
        # functions
        for name, f in self.funcs.items():
            self.func(name, f)
        for (pos, name, line) in self.fixups:
            f = self.funcs[name]
            self.code[pos] = f['addr'] & 255
            self.code[pos + 1] = (f['addr'] >> 8) & 255
            self.code[pos + 3] = f['nloc']
        if len(self.code) > R.CODE_MAX:
            self.err('code too big: %d bytes (max %d)' % (len(self.code), R.CODE_MAX))
        while len(self.mem_init) > self.mem_words:
            self.mem_init.pop()

    def func(self, name, f):
        node = f['node']
        self.line = node[4]
        f['addr'] = len(self.code)
        self.loc = {}
        for p in node[2]:
            if p in self.loc:
                self.err('duplicate parameter %r' % p)
            self.loc[p] = len(self.loc)
        self.loops = []
        self.fname = name
        self.block(node[3])
        self.push(0)
        self.op('RET')
        f['nloc'] = len(self.loc)
        if f['nloc'] > 60:
            self.err('function %r has too many locals' % name)

    def call_user(self, name, nargs, line):
        if name not in self.funcs:
            self.err('unknown function %r' % name, line)
        f = self.funcs[name]
        if f['nargs'] != nargs:
            self.err('%s() takes %d arguments, got %d' % (name, f['nargs'], nargs), line)
        self.code.append(R.CORE['CALL'])
        self.fixups.append((len(self.code), name, line))
        self.code += b'\0\0' + bytes((nargs, 0))

    # --- statements ---
    def block(self, node):
        for s in node[1]:
            self.stmt(s)

    def declare_local(self, n, line):
        if self.loc is None:
            self.err('internal')
        if n in self.consts or n in self.arrays:
            self.err('%r clashes with a constant/array' % n, line)
        if n not in self.loc:
            self.loc[n] = len(self.loc)
        return self.loc[n]

    def stmt(self, s):
        k = s[0]
        self.line = s[-1] if isinstance(s[-1], int) else self.line
        if k == 'block':
            self.block(s)
        elif k == 'vars':
            for (n, init, ln) in s[1]:
                slot = self.declare_local(n, ln)
                if init is not None:
                    self.expr(init)
                else:
                    self.push(0)
                self.op('STL', slot)
        elif k == 'assign':
            self.assign(s)
        elif k == 'expr':
            e = s[1]
            ret = self.call(e, want=False)
            if ret:
                self.op('DROP')
        elif k == 'if':
            self.expr(s[1])
            jz = self.jump('JZ')
            self.stmt(s[2])
            if s[3] is not None:
                je = self.jump('JMP')
                self.patch(jz)
                self.stmt(s[3])
                self.patch(je)
            else:
                self.patch(jz)
        elif k == 'while':
            top = len(self.code)
            self.expr(s[1])
            jz = self.jump('JZ')
            self.loops.append((top, [], []))
            self.stmt(s[2])
            self.jump_to('JMP', top)
            _, brks, conts = self.loops.pop()
            self.patch(jz)
            for b in brks:
                self.patch(b)
            for c in conts:
                self.patch(c, top)
        elif k == 'for':
            if s[1] is not None:
                self.stmt(s[1])
            top = len(self.code)
            jz = None
            if s[2] is not None:
                self.expr(s[2])
                jz = self.jump('JZ')
            self.loops.append((top, [], []))
            self.stmt(s[4])
            step = len(self.code)
            if s[3] is not None:
                self.stmt(s[3])
            self.jump_to('JMP', top)
            _, brks, conts = self.loops.pop()
            if jz is not None:
                self.patch(jz)
            for b in brks:
                self.patch(b)
            for c in conts:
                self.patch(c, step)
        elif k == 'break':
            if not self.loops:
                self.err('break outside a loop')
            self.loops[-1][1].append(self.jump('JMP'))
        elif k == 'continue':
            if not self.loops:
                self.err('continue outside a loop')
            self.loops[-1][2].append(self.jump('JMP'))
        elif k == 'return':
            if s[1] is not None:
                self.expr(s[1])
            else:
                self.push(0)
            self.op('RET')
        else:
            self.err('internal: statement %r' % k)

    def lookup(self, n, line):
        if n in self.loc:
            return ('L', self.loc[n])
        if n in self.globals:
            return ('G', self.globals[n])
        return None

    def assign(self, s):
        _, target, op, rhs, line = s
        self.line = line
        binop = None if op == '=' else BIN_OPS[op[:-1]]
        if target[0] == 'name':
            n = target[1]
            v = self.lookup(n, line)
            if v is None:
                if n in self.consts or n in self.arrays:
                    self.err('cannot assign to %r' % n, line)
                # implicit local declaration on first assignment is NOT allowed
                self.err('unknown variable %r (declare it with var)' % n, line)
            ld, st = ('LDG', 'STG') if v[0] == 'G' else ('LDL', 'STL')
            if binop:
                self.op(ld, v[1])
                self.expr(rhs)
                self.op(binop)
            else:
                self.expr(rhs)
            self.op(st, v[1])
        else:  # array element
            self.array_addr(target)
            if binop:
                self.op('DUP')
                self.op('LDM')
                self.expr(rhs)
                self.op(binop)
            else:
                self.expr(rhs)
            self.op('STM')

    def array_addr(self, e):
        n = e[1]
        if n not in self.arrays:
            self.err('%r is not an array' % n, e[3])
        base, sz = self.arrays[n]
        self.expr(e[2])
        if base:
            self.push(base)
            self.op('ADD')
        # runtime bound check: the VM checks 0 <= addr < memWords; indexing past this array's end but inside
        # another array is a cart bug the VM cannot see.  We add a per-array clamp check for safety.
        self.push(base)
        self.push(base + sz - 1)
        self.op('CLAMP')

    # --- expressions ---
    def expr(self, e):
        k = e[0]
        self.line = e[-1] if isinstance(e[-1], int) else self.line
        if k == 'num':
            self.push(e[1])
        elif k == 'str':
            self.push(self.string(e[1]))
        elif k == 'name':
            n = e[1]
            v = self.lookup(n, e[2])
            if v:
                self.op('LDG' if v[0] == 'G' else 'LDL', v[1])
            elif n in self.consts:
                self.push(self.consts[n])
            elif n in self.arrays:
                self.push(self.arrays[n][0])
            else:
                self.err('unknown name %r' % n, e[2])
        elif k == 'idx':
            self.array_addr(e)
            self.op('LDM')
        elif k == 'un':
            self.expr(e[2])
            self.op({'-': 'NEG', '!': 'LNOT', '~': 'NOT'}[e[1]])
        elif k == 'bin':
            o = e[1]
            if o == '&&':
                self.expr(e[2])
                j0 = self.jump('JZ')
                self.expr(e[3])
                self.op('LNOT'); self.op('LNOT')
                je = self.jump('JMP')
                self.patch(j0)
                self.push(0)
                self.patch(je)
            elif o == '||':
                self.expr(e[2])
                j1 = self.jump('JNZ')
                self.expr(e[3])
                self.op('LNOT'); self.op('LNOT')
                je = self.jump('JMP')
                self.patch(j1)
                self.push(1)
                self.patch(je)
            else:
                self.expr(e[2])
                self.expr(e[3])
                self.op(BIN_OPS[o])
        elif k == 'tern':
            self.expr(e[1])
            jz = self.jump('JZ')
            self.expr(e[2])
            je = self.jump('JMP')
            self.patch(jz)
            self.expr(e[3])
            self.patch(je)
        elif k == 'call':
            if not self.call(e, want=True):
                self.err('%s() does not return a value' % e[1], e[3])
        else:
            self.err('internal: expr %r' % k)

    def call(self, e, want):
        """Emits a call.  Returns True if it leaves a value on the stack."""
        _, name, args, line = e
        self.line = line
        if name in R.BUILTINS:
            opc, nargs, ret = R.BUILTINS[name]
            if len(args) != nargs:
                self.err('%s() takes %d arguments, got %d' % (name, nargs, len(args)), line)
            for a in args:
                self.expr(a)
            self.code.append(opc)
            return bool(ret)
        for a in args:
            self.expr(a)
        self.call_user(name, len(args), line)
        return True


# ----------------------------------------------------------------------------------------
# cart assembly
# ----------------------------------------------------------------------------------------
def default_consts():
    c = {}
    for i, n in enumerate(R.COLOR_NAMES):
        c[n] = i
    c.update(LEFT=0, RIGHT=1, UP=2, DOWN=3, A=4, B=5, SW=160, SH=128, TRUE=1, FALSE=0)
    return c


def parse_rows(args, what, n=8):
    rows = [a[1] for a in args if a[0] == 's']
    if len(rows) != n:
        raise CompileError('%s needs %d row strings of 8 characters' % (what, n))
    out = []
    for r in rows:
        if len(r) != 8:
            raise CompileError('%s row %r is not 8 characters' % (what, r))
        v = 0
        for i, ch in enumerate(r):
            if ch in '#Xx*':
                v |= 0x80 >> i
        out.append(v)
    return out


def fixed(s, n, what):
    b = s.encode('latin1')
    if len(b) > n:
        raise CompileError('%s %r is longer than %d characters' % (what, s, n))
    return b.ljust(n, b'\0')


def compile_source(src, fname='cart'):
    code_text, dirs = split_directives(src)
    meta = dict(name=None, blurb='', author='', version=1, color=8, twop=False, lower=False,
                tiers=['NORMAL', 'EASY', 'HARD', 'EXTREME'], help=[], icon=None)
    sprites = []
    consts = default_consts()
    for (ln, d, args) in dirs:
        try:
            if d == 'name':
                meta['name'] = args[0][1]
            elif d == 'blurb':
                meta['blurb'] = args[0][1]
            elif d == 'author':
                meta['author'] = args[0][1]
            elif d == 'version':
                meta['version'] = int(args[0][1])
            elif d == 'color':
                c = args[0][1].upper()
                meta['color'] = R.COLOR_NAMES.index(c) if c in R.COLOR_NAMES else int(c)
            elif d == 'twoplayer':
                meta['twop'] = True
            elif d == 'lower':
                meta['lower'] = True
            elif d == 'tiers':
                t = [a[1] for a in args]
                if len(t) != 4:
                    raise CompileError('@tiers needs 4 names')
                meta['tiers'] = t
            elif d == 'help':
                meta['help'] = [a[1] for a in args][:3]
            elif d == 'icon':
                meta['icon'] = parse_rows(args, '@icon')
            elif d == 'sprite':
                name = args[0][1]
                sprites.append(parse_rows(args[1:], '@sprite ' + name))
                if not re.match(r'^[A-Za-z_]\w*$', name):
                    raise CompileError('bad sprite name %r' % name)
                consts[name] = len(sprites) - 1
            else:
                raise CompileError('unknown directive @%s' % d)
        except CompileError as e:
            raise CompileError('line %d: %s' % (ln, e))
        except (IndexError, ValueError) as e:
            raise CompileError('line %d: bad @%s directive (%s)' % (ln, d, e))
    if not meta['name']:
        raise CompileError('missing @name')
    if meta['icon'] is None:
        raise CompileError('missing @icon')
    if len(sprites) > R.SPR_MAX:
        raise CompileError('too many sprites (max %d)' % R.SPR_MAX)
    toks = lex(code_text)
    items = P(toks).program()
    g = Gen(items, consts)
    g.build()
    mem_init = [w16(v) for v in g.mem_init]
    code, strs = bytes(g.code), bytes(g.strs)
    spr = b''.join(bytes(s) for s in sprites)
    pay = code + strs + spr + struct.pack('<%dh' % len(mem_init), *mem_init)
    flags = (1 if meta['twop'] else 0) | (2 if meta['lower'] else 0)
    hdr = bytearray(R.HDR_SIZE)
    hdr[0:4] = b'ARC1'
    hdr[4] = 1
    struct.pack_into('<BBBHHHHHHIBB', hdr, 5, flags, meta['version'] & 255, len(sprites), len(code), len(strs),
                     g.mem_words, len(mem_init), g.init_addr, g.frame_addr, R.fnv1a(pay), len(g.globals),
                     meta['color'] & 15)
    hdr[32:48] = fixed(meta['name'], 15, 'name').ljust(16, b'\0')
    hdr[48:72] = fixed(meta['blurb'], 23, 'blurb').ljust(24, b'\0')
    hdr[72:88] = fixed(meta['author'], 15, 'author').ljust(16, b'\0')
    for i, t in enumerate(meta['tiers']):
        hdr[88 + i * 8: 96 + i * 8] = fixed(t, 7, 'tier name').ljust(8, b'\0')
    hdr[120:128] = bytes(meta['icon'])
    for i, h in enumerate(meta['help']):
        hdr[128 + i * 24: 152 + i * 24] = fixed(h, 23, 'help line').ljust(24, b'\0')
    blob = bytes(hdr) + pay
    if len(blob) > 14000:
        raise CompileError('cart too big (%d bytes)' % len(blob))
    return blob, meta, g


def compile_file(path):
    src = open(path, encoding='latin1').read()
    try:
        return compile_source(src, path)
    except CompileError as e:
        raise CompileError('%s: %s' % (os.path.basename(path), e))


# ----------------------------------------------------------------------------------------
# self-test: scripted bots
# ----------------------------------------------------------------------------------------
def bot_random(seed):
    rnd = random.Random(seed)
    state = {'mask': 0, 'until': 0}

    def bot(f, vm):
        if f >= state['until']:
            state['mask'] = rnd.choice([0, 1, 2, 4, 8, 16, 32, 1 | 16, 2 | 16, 4 | 16, 8 | 16, 16 | 32, 1 | 4, 2 | 8, 0])
            state['until'] = f + rnd.randint(1, 20)
        return state['mask']
    return bot


def bot_mash(f, vm):
    return (16 if f % 6 < 3 else 0) | (32 if f % 11 < 2 else 0)


def bot_idle(f, vm):
    return 0


def bot_sweep(f, vm):
    ph = (f // 30) % 4
    return [1, 4, 2, 8][ph] | (16 if f % 8 < 4 else 0)


BOTS = [('idle', lambda s: bot_idle), ('mash', lambda s: bot_mash), ('sweep', lambda s: bot_sweep),
        ('random', bot_random)]

# per-cart extra checks: name -> list of (description, fn(path, blob) -> None or raises AssertionError)
CART_CHECKS = {}


def test_cart(path, frames=1500, verbose=True):
    blob = open(path, 'rb').read()
    cart = R.Cart(blob)
    worst = 0
    overs = 0
    scores = []
    runs = [(0, 'idle', 1), (0, 'mash', 1), (0, 'sweep', 1), (1, 'sweep', 2)] + [(t, 'random', 3 + t) for t in range(4)]
    for tier, bname, seed in runs:
        mk = dict(BOTS)[bname]
        vm = R.run_cart(blob, frames=frames, bot=mk(seed * 7919 + tier), tier=tier, seed=seed * 104729 + tier, render=False)
        worst = max(worst, vm.max_ops)
        if vm.over:
            overs += 1
        scores.append(vm.score_v)
    if worst > R.BUDGET * 0.6:
        raise AssertionError('%s: worst frame used %d ops (budget %d)' % (cart.name, worst, R.BUDGET))
    chk = CART_CHECKS.get(os.path.splitext(os.path.basename(path))[0])
    if chk:
        chk(path, blob)
    if verbose:
        print('  ok  %-14s %5d B  maxops %5d  game-overs %d/8  best score %s' %
              (cart.name, len(blob), worst, overs, max(scores)))
    return worst, overs, max(scores)


def write_shot(path, out_dir, frames=240):
    blob = open(path, 'rb').read()
    vm = R.run_cart(blob, frames=frames, bot=bot_sweep)
    os.makedirs(out_dir, exist_ok=True)
    R.dump_png(vm, os.path.join(out_dir, os.path.splitext(os.path.basename(path))[0] + '.png'))



# ----------------------------------------------------------------------------------------
# collision guard: expansion carts must not duplicate a built-in game
# ----------------------------------------------------------------------------------------
GENRE_WORDS = ['lander', 'landing', 'invader', 'breakout', 'brick', 'brix', 'frogger', 'hopper', 'pong', 'snake',
               'tetris', 'racer', 'racing', 'memory', 'pairs', 'pacman', 'asteroid', 'meteor', 'dodge', 'whack',
               'mole', 'zap', 'runner', 'platform', 'minesweeper', 'simon', 'sokoban', 'reversi', 'checkers',
               'chess', 'wordle', 'hangman', 'sudoku', 'plinko', 'slots', 'blaster', 'hockey', 'mastermind']


def _norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())


def builtin_names():
    names = []
    txt = os.path.join(HERE, 'builtin_games.txt')
    if os.path.exists(txt):
        names += [l.strip() for l in open(txt, encoding='utf8') if l.strip() and not l.startswith('#')]
    ino = os.path.join(HERE, '..', 'PyGamerPortal.ino')
    if os.path.exists(ino):
        s = open(ino, encoding='utf8', errors='ignore').read()
        i = s.find('kGameNames[NUM_GAMES] = {')
        if i >= 0:
            j = s.find('};', i)
            names += re.findall(r'"([^"]+)"', s[i:j])
    return sorted(set(names))


def collision_check(name, blurb=''):
    """Returns (errors, warnings) for a cart called `name`."""
    errs, warns = [], []
    n = _norm(name)
    for b in builtin_names():
        bn = _norm(b)
        if not bn:
            continue
        if n == bn or (len(bn) >= 4 and bn in n) or (len(n) >= 4 and n in bn):
            errs.append('name "%s" collides with built-in game "%s"' % (name, b))
    for w in GENRE_WORDS:
        if w in n:
            errs.append('name "%s" uses genre keyword "%s" (a built-in game already covers that genre)' % (name, w))
        elif w in _norm(blurb):
            warns.append('blurb of "%s" mentions genre keyword "%s" (a built-in game covers it)' % (name, w))
    return errs, warns


def main(argv):
    args = [a for a in argv if not a.startswith('--')]
    flags = [a for a in argv if a.startswith('--')]
    os.makedirs(OUT_DIR, exist_ok=True)
    built = []
    if '--test-only' not in flags:
        srcs = args or sorted(glob.glob(os.path.join(SRC_DIR, '*.arcl')))
        if not srcs:
            print('no sources in', SRC_DIR)
            return 1
        for s in srcs:
            blob, meta, g = compile_file(s)
            errs, warns = collision_check(meta['name'], meta.get('blurb', ''))
            for w in warns:
                print('WARNING:', os.path.basename(s), w)
            if errs:
                raise CompileError('%s: BUILT-IN GAME COLLISION: %s. Pick a different, original game.' % (os.path.basename(s), '; '.join(errs)))
            out = os.path.join(OUT_DIR, os.path.splitext(os.path.basename(s))[0] + '.arc')
            open(out, 'wb').write(blob)
            built.append(out)
            print('built %-10s %-14s %5d bytes (code %d, strings %d, mem %d words, %d globals)' %
                  (os.path.basename(out), meta['name'], len(blob), len(g.code), len(g.strs), g.mem_words, len(g.globals)))
    else:
        built = sorted(glob.glob(os.path.join(OUT_DIR, '*.arc')))
    if '--no-test' in flags:
        return 0
    print('self-test (8 scripted runs of 1500 frames per cart):')
    bad = 0
    for p in built:
        try:
            test_cart(p)
        except (AssertionError, R.CartError) as e:
            bad += 1
            print('  FAIL', os.path.basename(p), e)
        if '--shots' in flags:
            write_shot(p, os.path.join(HERE, 'out', 'shots'))
    print('%d carts, %d failed' % (len(built), bad))
    return 1 if bad else 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except CompileError as e:
        print('COMPILE ERROR:', e)
        sys.exit(1)
