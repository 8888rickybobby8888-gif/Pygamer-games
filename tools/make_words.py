#!/usr/bin/env python3
"""Builds tools/out/words.txt for Hangman and Wordle (no downloads, no extra packages).

The word lists are curated and written right here: common 5-letter words (used by Wordle and
Hangman) plus shorter and longer common words (Hangman only). Output: one lower-case word per
line, a-z only, sorted, no duplicates. Install it on the PyGamer drive as /data/words.txt with
    powershell -ExecutionPolicy Bypass -File install_assets.ps1 -Words
You can add your own words to EXTRA_WORDS below (or edit the lists) and run this again.
"""
import os, sys

FIVE = """
about above abuse actor acute admit adopt adult after again agent agree ahead alarm album alert alike alive allow alone along alter among anger angle angry
ankle apart apple apply arena argue arise armor array arrow aside asset avoid awake award aware awful bacon badge badly baker bases basic basis beach beard
beast begin being belly below bench berry birth black blade blame blank blast blaze bleed blend bless blind blink block blood bloom blown blues bluff blunt
board boast boost booth bound brain brake brand brave bread break breed brick bride brief bring broad broke brown brush buddy build built bunch burst buyer
cabin cable camel candy canoe cargo carry carve catch cause cease chain chair chalk champ chaos charm chart chase cheap cheat check cheek cheer chess chest
chick chief child chill chime china chirp choir chose chunk cider cigar civic claim clash class clean clear clerk click cliff climb cling clock clone close
cloth cloud clown clubs coach coast cobra cocoa comet comic coral couch cough could count court cover crack craft crane crash crawl crazy cream creek creep
crest crime crisp cross crowd crown crude cruel crush crust curly curve cycle daily dairy daisy dance dealt death debut decay delay delta dense depth derby
desks devil diary digit diner dirty disco ditch diver dizzy dodge doing donor doubt dough dozen draft drain drama drank drawn dream dress dried drift drill
drink drive drown drums dryer ducks dully dusty dwarf dwell eager eagle early earth easel eaten edges eight elbow elder elect elite empty enemy enjoy enter
entry equal error essay event every exact exams exist extra fable faint fairy faith false fancy fatal fault feast fence ferry fever fewer fiber field fifth
fifty fight final finds fires first fixed flame flash fleet flesh flick flies fling float flock flood floor flour fluid flush flute focus foggy force forge
forgo forth forty forum found frame frank fraud freak fresh fried front frost fruit fully funny fuzzy gamer gauge genre ghost giant given glade glass glide
globe gloom glory glove going grace grade grain grand grant grape graph grasp grass grave great greed green greet grief grill grind groan groom group grove
grown guard guess guest guide guilt habit hairy handy happy hardy harsh haste hasty hatch haunt haven heart heavy hedge hello hence herbs hobby hockey honey
honor horse hotel hound house human humor hurry ideal image imply index inner input irony issue ivory jazzy jelly jewel joint jolly judge juice juicy jumbo
jumpy kayak keeps knack kneel knife knock known label labor lace lance large laser later laugh layer leads leafy learn lease least leave legal lemon level
lever light lilac limit linen liner lived liver lives llama loads loaf local lodge logic loose lover lower loyal lucky lunar lunch lying magic major maker
mango maple march marsh mason match mayor meals meant medal media melon mercy merge merit merry metal meter micro might minor minus mirth mixed model moist
money month moral motel motor mount mouse mouth movie muddy music myths naive naval needs nerve never newly night ninja noble noise north notch noted novel
nurse nylon oasis occur ocean offer often olive onion opera orbit order organ other otter ought ounce outer owner oxide ozone paint pairs panel panic paper
party pasta patch pause peace peach pearl pedal penny perch phase phone photo piano piece pilot pinch pitch pixel pizza place plain plane plank plant plate
plaza plead pluck plumb plume plump plush poems point poker polar polka porch pound power prank prawn press price pride prime print prior prism prize probe
proof proud prove pulse punch pupil puppy purse queen query quest queue quick quiet quilt quirk quite quota quote radar radio raise rally ranch range rapid
ratio reach react ready realm rebel refer reign relax relay renew reply rhyme rider ridge rifle right rigid ripen risky rival river roast robin robot rocky
rodeo rogue roman roots rough round route royal rugby ruins ruler rumor rural sadly safer saint salad sales salon sandy sauce saved scale scarf scene scent
scoop scope score scout scrap screw seeds seize sense serve seven shade shake shall shame shape share shark sharp shave sheep sheer sheet shelf shell shift
shine shiny shirt shock shoes shoot shore short shout shown shrug sight sigma silly since sixth sixty sized skate skill skirt skull slate sleep slice slide
slime slope small smart smell smile smoke snack snail snake sneak snowy soapy sober solar solid solve sonic sorry sound south space spare spark speak speed
spell spend spice spicy spike spill spine spoil spoon sport spray squad stack staff stage stain stair stake stale stamp stand stare start state stays steak
steal steam steel steep steer stern stick stiff still sting stock stone stood stool store storm story stove strap straw stray strip stuck study stuff style
sugar suite sunny super surge swamp swarm swear sweat sweep sweet swept swift swing swirl sword syrup table tacos taken tales talks tango tapes taste taught
teach teams tears teeth tempo tenor tense tenth tents terms thank theft theme there thick thief thing think third thorn those three threw throw thumb thump
tidal tiger tight timer times tired title toast today token tooth topic torch total touch tough towel tower toxic trace track trade trail train trait trash
treat trees trend trial tribe trick tried tries troop truck truly trump trunk trust truth tulip tummy tuner tunes twice twins twist ultra uncle under unify
union unite unity until upper upset urban usage usual valid value valve vases vault venue verse video views villa vinyl viola viper virus visit vital vivid
vocal vodka voice voter wages wagon waist walks waste watch water waves weary weave wedge weeds weigh weird whale wheat wheel where which while whirl white
whole whose widen widow width wield windy wings witch woman women woods words world worry worse worst worth would wound woven wrist write wrong yacht yield
young youth zebra zesty zones
alley amber ample angel anvil arbor ashes attic aunty bagel banjo barge baron beads beams bells bikes bingo birds bison blimp bloke bobby bonus boots bowls
boxer brass brook broom bucks bulbs bulls cabin camps canal cards cards carol cedar chefs chime cliff clips clubs coins colon cones cooks cords cores corks
crabs crepe crews crops cubes cults cupid darts dates decor deeds deers dials dimes disks docks dolls doors dorms downs drops drums ducks dunes earns easel
eaves egret elves ember emote ended envoy epoch equip erase evict exile fails fairs farms fawns feeds fells fiery files films finch firms fists flaps flats
flaws fleas flies flips flora foams folds folks fonts foods fools foots forks forms forts fowls frogs fumes funds gates gears gecko gifts girls glows goats
goods goose grams grips grows gulls gusts hands hares harps hawks hazel heaps heels hills hinge hints hoods hooks hoops hopes horns hosts hours hubby hulls
humps icons idols igloo inbox ideas jeans jeeps jokes jumps kites knees knobs knots koala lakes lambs lamps lands lanes larks lasso latch lawns leaps ledge
lends lifts lilies limbs lines links lions lists lions lobby locks lofts logos looks loops lords lorry lotus lungs lured lyric mails maids malls maple marks
masks masts mazes meats mends menus mimic mints mists moats molds monks moods moons mound moves mules nails names naps necks nests nodes noses notes
novas oaths ocean opals ovals ovens packs pages pails pants parks parts paths paws peaks pears pecan pegs pens perks pests petal phone picks piers pikes
pills pines pipes plots plugs plums poets polls ponds pools ports posts pours prays prods pubs pumps pupae quail quays quiz rails rains rakes rates reels
rents rests rhino rings rinks rises roads roars robes rocks roles rolls roofs rooms roots ropes roses rules runes rungs rusty sacks safes sails saves scans
seats seeks sells sends serum shaft shelf shops shows sides sighs signs silks sinks sites skies skips slabs slaps sleds slots slows smash snaps snows socks
sofas songs sorts souls soups spans spies spins spots stars stems steps stews stops straw strum suits sunny surfs swans swaps swims tails talon tanks tasks
taxis teams tells tends tests texts thaws tides tiles tills tints tires toads toes tolls tombs tones tools tops tours towns toys trams traps trays trees
tribe trips trout tubes tunes turns twigs types unity urges vases veils veins vests vines vowel wails walls wands wants wares warms waves ways wells whips
wicks wilds winds wines wires wolves woods wools yards yarns yawns years yells zeros zings
""".split()

SHORT = """
able acid aged also area army away baby back ball band bank base bath bear beat been bell belt best bike bill bird blow blue boat body bold bone book boom
born boss both bowl bulk burn bush busy cafe cake call calm came camp card care cart case cash cast cats cave cell chat chef chip city clay club coal coat
code coin cold come cook cool cope copy cord core cost crew crop dark data date dawn days dead deal dean dear deck deep deer desk dial dice diet dirt dish
dive dock does dogs doll done door dose down draw drew drop drum duck dull dust duty each earn ears east easy edge else even ever evil exit face fact fail
fair fall farm fast fate fear feed feel feet fell felt file fill film find fine fire firm fish five flag flat flew flow food foot ford form fort four free
frog from fuel full fund gain game gate gave gear gift girl give glad goal goat gold golf gone good gray grew grid grow gulf hair half hall hand hang hard
harm hate have head hear heat held hell help here hero hide high hill hint hold hole home hope horn host hour huge hunt hurt idea inch into iron isle item
jack jazz join joke jump june jury just keen keep kept kick kill kind king kiss knee knew know lack lady laid lake lamp land lane last late lawn lead leaf
lean left lend less life lift like lime line link lion list live load loan lock logo long look loop lord lose loss lost loud love luck lump lung made mail
main make male mall many mark mask mass mate meal mean meat meet melt menu mere mild mile milk mill mind mine mint miss mode mood moon more most move much
must myth nail name navy near neat neck need nest news next nice nine none noon norm nose note noun odds okay once only onto open oral oven over pace pack
page paid pain pair palm park part pass past path peak pear peel pick pier pile pine pink pipe plan play plot plug plus poem poet pole poll pond pool poor
port pose post pour pray pull pump pure push quit race rack rain rank rare rate read real rear rely rent rest rice rich ride ring rise risk road rock role
roll roof room root rope rose rule rush safe sail salt same sand save seat seed seek seem seen self sell send sent ship shoe shop shot show shut sick side
sign silk sing sink site size skin skip slim slip slow snow soap sock soft soil sold sole some song soon sort soul soup spot star stay stem step stir stop
such suit sure swim tail take tale talk tall tank tape task team tear tell tent term test text than that thee them then they thin this thus tide tidy tile
time tiny tips tire told toll tone took tool tops tour town toys tree trim trip true tube tune turn twin type unit upon urge used user vary vast very view
vote wage wait wake walk wall want warm wash wave ways weak wear week well went were west what when whom wide wife wild will wind wine wing wire wise wish
with wolf wood wool word wore work worm wrap yard yarn year yoga your zero zone
""".split()

LONG = """
absolute accident account achieve activity address advance adventure airplane airport alphabet amazing ancient animal another anything apartment appetite
arrange article athlete attempt audience average backpack balance balloon bamboo bandage banquet barbecue basket battery beautiful because bedroom
beginning believe benefit bicycle biology birthday blanket blizzard bonfire bookshelf borrow bottle boundary bracelet breakfast bridge brilliant broccoli
building butter butterfly cabbage calendar camera campfire candle capital captain caravan careful carnival carpet carrot castle catalog caterpillar
cathedral ceiling celebrate cement century certain chairman challenge champion channel chapter character charcoal chicken children chimney chocolate
circle circuit circus citizen classic climate clothing cloudy coconut collect college comedy comfort company compass complete computer concert conduct
confirm connect consider control cookie copper corner costume cottage cotton country courage cousin cracker crayon creature cricket crocodile cucumber
curious current curtain custom cycling dancing danger daughter december decide declare decorate delicate delight deliver dentist describe desert design
dessert destroy detail develop diamond diary different dinner dinosaur direction discover distance doctor dolphin dominoes donkey double dragon drawing
dream dresser driver dumpling eagle earth earthquake echo eclipse economy edition education eighteen elbow electric elephant elevator emerald emperor empty
energy engine english enormous entire entrance envelope equal escape evening example excellent exchange excite exercise explain explore express
fabric factory family famous farmer fashion feather february festival fiction fifteen figure finger fireplace fireworks fisherman flashlight flavor
flower flying football forest forever forget fortune fountain freedom friend frozen furniture future galaxy gallery garage garden gather general gentle
giraffe glacier glasses global goldfish gorilla gossip government grandfather grandmother grape grasshopper gravity grocery growth guitar hamburger
hammer handle happen harbor harvest hashtag hedgehog helicopter helmet history holiday honest horizon hospital hundred hunger hurricane husband iceberg
ignore imagine impress improve include increase indoor industry insect inside instant instrument interest internet island jacket january jellyfish
jewelry journey jungle junior kangaroo keyboard kitchen kitten kingdom ladder lantern laptop laughter lawyer leader leather lecture legend leopard
lesson letter library lightning lobster lollipop machine magazine magnet mammal manager mansion marathon market marvel mattress meadow measure medicine
melody member memory message method midnight million miracle mirror mission mistake mixture modern moment monkey monster morning mosquito mother motorcycle
mountain mouse muffin museum mushroom musician mystery napkin narrow nature necklace needle neighbor nephew network nickel night nineteen noodle normal
notebook nothing november nurse object ocean october octopus office officer onion orange orchestra ordinary organize original outside oxygen package
paddle painter palace pancake panda paper parade parent parrot partner passenger pasta pattern peanut pelican pencil penguin people pepper perfect perform
picture pillow pilot pineapple pirate planet plastic platform player pleasant pocket poetry polite popcorn portrait potato powder practice present pretty
princess printer prison problem produce program project promise protect pumpkin puppet puzzle pyramid quarter question quickly rabbit radio railway
rainbow raincoat reason receive record recycle reflect refrigerator regular relative remember repair report rescue restaurant result return reward
riddle river robot rocket rooster sailor salad sandwich satellite saturday saucer sausage scarf school science scissors scooter scorpion screen season
second secret seesaw seventeen shadow shampoo shelter shiver shoulder shovel shower silver simple singer sister sixteen skeleton skateboard sleeping
slipper smooth snowman soccer soldier solution someone special spider spinach sponge spring squirrel stadium station steady stomach storm story
straight strange stream street strong student subject submarine success summer sunflower sunrise sunset supper surface surprise sweater swimming symbol
system table teacher telephone telescope tennis theater thermometer thousand thunder ticket tiger tomato tonight tooth tornado tortoise tourist towel
tractor traffic train travel treasure triangle trophy trouble truck trumpet tunnel turkey turtle twelve twenty umbrella uncle uniform universe upstairs
vacation valley vegetable velvet vessel village violin visitor volcano volleyball wagon waiter walrus warrior washing wasp watch waterfall weather
wedding weekend whale wheel whisper whistle window winter wizard wonder woodpecker worker world wrinkle yellow yogurt zebra zipper
""".split()

EXTRA_WORDS = []   # add your own words here

def main():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
    os.makedirs(out_dir, exist_ok=True)
    words = set()
    for w in FIVE + SHORT + LONG + EXTRA_WORDS:
        w = w.strip().lower()
        if w.isascii() and w.isalpha() and 3 <= len(w) <= 10:
            words.add(w)
    words = sorted(words, key=lambda w: (len(w), w))
    path = os.path.join(out_dir, "words.txt")
    with open(path, "w", newline="\n") as f:
        f.write("\n".join(words) + "\n")
    by_len = {}
    for w in words:
        by_len[len(w)] = by_len.get(len(w), 0) + 1
    five = by_len.get(5, 0)
    print("wrote %s: %d words (%d bytes)" % (path, len(words), os.path.getsize(path)))
    print("by length:", ", ".join("%d:%d" % (k, by_len[k]) for k in sorted(by_len)))
    if five < 100:
        print("ERROR: fewer than 100 five-letter words")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
