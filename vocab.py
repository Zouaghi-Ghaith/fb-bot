"""
The "word brain": Tunisian Darija vocabulary, ideal answer examples, address / phone / location rules,
and a list of NON-Tunisian words the bot must never use.

You can edit everything here (you are the native speaker!). brain.py reads this file.
Bigger lists = better understanding, but each customer message costs a few more tokens.
"""
import re

# ---------------------------------------------------------------------------------------------
# 1) DICTIONARY (what customers write -> meaning). The AI also knows much more; this guides it.
# ---------------------------------------------------------------------------------------------
TUNISIAN_VOCAB = """
TUNISIAN DARIJA DICTIONARY. Customers write in Latin letters ("Arabizi": 3=ع 7=ح 9=ق 5=خ 8=غ 2=ء) or Arabic script,
often mixed with French. Spelling varies a lot.

GREETINGS AND POLITENESS
- 3aslema / aslema / salem / 3aslema 3lik / عسلامة / سلام = hello
- sba7 el khir / صباح الخير = good morning ; msa el khir / 3chiya / مساء الخير = good evening
- marhba / marhba bik / مرحبا بيك = welcome
- chbik / chnowa a7welek / labes / labes 3lik / لاباس = how are you ; el 7amdoulleh / الحمدلله = fine, thanks
- ya3tik essa7a / yaatik essaha / يعطيك الصحة / sa7it / saha = thank you ; mersi barcha = thanks a lot
- sma7ni / smo7ni / سامحني = sorry / excuse me ; ma3lich / ma3lesh / معليش = no problem
- min fadhlek / mel fadhlek / من فضلك = please
- besslema / 3la slema / بالسلامة = goodbye ; inchallah / إن شاء الله = God willing

YES / NO / BASICS
- iyeh / ey / eh / آه / إيه = yes ; le / lé / لا = no ; behi / باهي / d'accord / okey = OK, good ; yezzi / يزي = enough
- barcha / برشا = a lot ; chwaya / شوية = a little ; kol / koul / كل = all ; kamel / كامل = whole / full ; 7aja / 7ajet / حاجة = thing(s)
- 3andek / 3andkom / عندك / عندكم = do you have ; 3andi / 3andna = I / we have ; ma3andich / ma3andnech = I / we don't have
- famma / fama / فما = there is, is there ; ma famech / ma fammech / ما فماش = there isn't
- mawjoud / mawjouda / موجود / موجودة = available ; mouch mawjouda / موش موجودة = not available ; mazelt / مازال = still
- mouch / mech / موش = not ; mouch mochkla / موش مشكلة = no problem ; ya3ni = I mean / so ; 3la 5ater = because
- ana / enti / howa / hiya / e7na / entouma / houma = I / you / he / she / we / you(pl) / they
- hedha / hedhi / hedhouma = this (m / f / pl) ; houni = here ; ehna = we ; 3andou / 3andha = he has / she has
- okhra / okher / okhrin = another / other ; ghir / bark = only ; zeda / zayed = also / more ; baddel / n9adder = change / I can

QUESTIONS AND REQUESTS
- chnowa / chnouwa / chneya / شنوة = what ; chkoun / شكون = who ; win / وين = where ; kifech / كيفاش = how
- 3lech / علاش = why ; wa9teh / وقتاش = when ; anehi / anehou / أنهي = which ; 9addech / 9addeh / 9deh / قداش = how much
- mnin = from where ; ta3mel / ta3mlou = you do ; tnajem / tnajjem / تنجم = can you ; nnajem / نجم = I can
- 9olli / 9ouli = tell me ; 3tini / 3titni / عطيني = give me ; ib3athli / eb3athli = send me ; ektebli = write to me
- warini / warrini / وريني = show me ; 3awenni = help me ; sa2elni = ask for me ; 3awed / te3awed = repeat
- nheb / نحب = I want ; theb / thebb / تحب = you want ; nheb nchri / nechri / نشري = I want to buy ; nheb n7ajez = I want to book
- nheb na3ref = I want to know ; nheb nchouf = I want to see ; nlawej 3la = I'm looking for ; yelzemni = I need
- bech / besh = will (future: bech nji = I will come) ; taw = now ; yezzi = stop ; 7ata = even / until

SHOPPING, PRICES, PAYMENT
- el prix / ethaman / الثمن = price ; ghali / غالي = expensive ; rkhis / رخيص = cheap ; ghali barcha = too expensive
- nezzel / nezzelli / نزّل = lower (the price) ; remise / réduction / promotion / solde = discount ; offre = offer ; gros = wholesale
- el khlas / khlas / الخلاص = payment ; nkhalles / نخلص = I pay ; flous / فلوس = money ; dinar / دينار / DT / TND = dinar ; mlim = millime
- cash / 3and el istilem / عند الاستلام = pay on delivery ; virement / carte bancaire / D17 / Flouci / mandat = payment methods people may ask about
- el commande / talab / طلب = order ; nsajjel / نسجل = I register ; nconfirmi / نأكد = I confirm ; n7ajez = I reserve
- el livraison / ettawsil / التوصيل = delivery ; twassel / ywassel = delivers ; livreur = delivery person ; frais de livraison = delivery fee
- retour / n3awed / nbaddel = return / exchange ; garantie = warranty ; facture = invoice ; stock = stock ; disponible = available
- taille (clothes) / pointure (shoes) / mi9yes / مقاس = size ; couleur / loun / لون = color ; modèle = model ; marque = brand ; qualité = quality
- colors: abyadh / byadh / أبيض = white ; k7al / كحل / noir = black ; a7mar / أحمر / rouge = red ; azra9 / أزرق / bleu = blue ;
  akhdhar / أخضر / vert = green ; asfar / أصفر / jaune = yellow ; ramadi / gris = gray ; wardi / rose = pink ; kahwi / marron = brown ;
  bnafsaji / violet = purple ; beige ; orange
- jdid / جديد = new ; 9dim = old ; kbir / sghir = big / small ; twil / 9sir = long / short ; mle7 / mleh / مليح = good ;
  mrigel / مريقل = great, perfect ; zina / zine = beautiful ; 5ayeb = bad ; 5fif / thkil = light / heavy
- NUMBERS: wa7ed 1, zouz / jouj 2, tletha 3, arba3a 4, khamsa 5, setta 6, sab3a 7, tmenya 8, tes3a 9, 3achra 10,
  7dhach 11, tnach 12, tletach 13, arba3tach 14, khamstach 15, settach 16, sba3tach 17, tmentach 18, tes3atach 19,
  3chrin 20, tlethin 30, arba3in 40, khamsin 50, settin 60, sab3in 70, tmanin 80, tes3in 90, mia 100, mitin 200, alf 1000.
  Prices: "mia w 3chrin dinar" = 120 dinars ; "khamsin dinar" = 50 dinars ; "alf" = 1000.

TIME
- taw / tawa / توا = now ; ghodwa / غدوة = tomorrow ; lyoum / el youm / اليوم = today ; el barah / البارح = yesterday
- ba3d ghodwa = day after tomorrow ; sba7 / sbe7 = morning ; dhohr = noon ; 3chiya = evening ; lil = night ; sa3a = hour
- 9rib / 9reb = soon, near ; fi a9reb wa9t = as soon as possible ; jomla / jem3a = week ; chhar = month
- days: el ithnin (Mon), ethlétha (Tue), el arba3 / lerb3a (Wed), el khemis (Thu), el jom3a (Fri), essebt (Sat), el a7ad (Sun)

COMPLAINTS AND HUMAN HELP
- mochkla / مشكلة = problem ; ghalta = mistake ; mouch behi = not good ; ma wselnich / ma jetnich el commande = my order did not arrive
- ta2khir / t2akhret = delay / it was late ; 5arrab / 5arbet = broken ; ghalet = wrong item ; nheb nrajja3 = I want to return
- rajja3li flousi = refund me ; zaa3ef / m9ayet = upset ; nheb nkallem wa7ed / nheb nkalem el responsable = I want to speak to someone
- 3andi mochkla fil commande = I have a problem with my order ; ma 3ejbetnich = I didn't like it ; behi mouch mli7 = not great

ADDRESSES AND LOCATIONS (accept ALL of these, in any order or language)
- adresse / 3onwen / عنوان = address ; ville / mdina = city ; gouvernorat / wilaya / ولاية = governorate ; 7ay / حي = neighborhood ;
  cité = housing area ; rue / nahj / نهج = street ; avenue / charia / شارع = avenue ; zenqa / زنقة = alley ; impasse = dead end ;
  résidence = residence ; immeuble / imm = building ; bloc = block ; etage / tabe9 / طابق = floor ; appartement / app / apt = apartment ;
  villa / dar = house ; lotissement = housing estate ; code postal = postal code ; 9ariya / 9arya = village ; mantiqa = area
- 9odem / قدام = in front of ; wara / ورا = behind ; janb / jemb / bjanb / جنب = next to ; 9rib men / قريب من = near ; bin ... w ... = between ;
  fi wost / في وسط = in the middle of ; foug / فوق = above ; te7t / تحت = below ; 3and = at ; ba3d / 9bal = after / before ;
  yemin / ysar / يمين / يسار = right / left ; fi 3a9eb = just after ; ta7t el jisr = under the bridge ; mel jiha = from the side of
- landmarks: pharmacie, café, boulangerie, école / madrasa, lycée, collège, faculté, mosquée / jem3a / jami3, sbitar / hôpital, poste, municipalité,
  banque, station (Agil, Total, Shell, Ola), louage / station louage, métro, TGM, gare, rond-point, carrefour (el carrefour), feu rouge (el feu),
  pont (jisr), souk / marché, stade, plage, Monoprix, Carrefour, Géant, Aziza, MG (Magasin Général), Ooredoo, Orange, Tunisie Telecom
- governorates: Tunis, Ariana, Ben Arous, Manouba, Nabeul, Zaghouan, Bizerte, Béja, Jendouba, Le Kef, Siliana, Sousse, Monastir, Mahdia,
  Kairouan, Kasserine, Sidi Bouzid, Sfax, Gabès, Médenine, Tataouine, Gafsa, Tozeur, Kébili
- common areas: Lac 1 / Lac 2, La Marsa, Carthage, Gammarth, Sidi Bou Said, La Goulette, El Menzah, Manar, Ennasr, Ghazela, Soukra, Raoued,
  Mourouj, Ezzahra, Hammam Lif, Rades, Bardo, Le Kram, Ariana Ville, Ettadhamen, Mnihla, Borj Cedria, Hammamet, Nabeul, Kelibia,
  Sousse Jawhara, Sahloul, Khezama, Kantaoui, Msaken, Monastir, Mahdia, Sfax Ville, Route Teniour, Route Gremda, Gabès Ville, Djerba (Houmt Souk, Midoun)
"""

# ---------------------------------------------------------------------------------------------
# 2) IDEAL ANSWERS (style examples). Facts always come from BUSINESS INFORMATION, never from here.
# ---------------------------------------------------------------------------------------------
STYLE_EXAMPLES = """
EXAMPLES OF THE STYLE TO USE (the facts in the examples are placeholders; use only the business information):

Tunisian Darija in Latin letters (customer writes Arabizi):
- Greeting: "3aslema ! Marhba bik 3andna 🌸 Chnowa nnajem n3awnek ?"
- Price: "El sneakers Classic b 120 dinar ✅ Chnowa el pointure elli thebha ?"
- Available: "Behi, famma pointure 42. Thebb nsajjel el commande ?"
- Not available: "Sma7ni, el pointure hedhi mouch mawjouda taw. Thebb pointure okhra ?"
- Delivery: "El livraison fi Tounes kol b 7 dinar, w twassel bin 24 w 72 sa3a. Fi anehi ville enti ?"
- Payment: "El khlas ykoun 3and el istilem, ya3ni tkhalles w enti tstalem el commande."
- Ask name: "Behi barcha ! Chnowa esmek el kamel ?"
- Ask phone: "W 3tini numro telifounek min fadhlek ?"
- Ask address: "Tamem. Win nab3athelek el commande ? Ektebli el adresse kima thebb (ville, 7ay wala rue, w 7ata 9rib men chnowa)."
- Address received: "Merci, 3andi el adresse ✅ Tamem."
- Order summary: "Tamem Sami ✅ Commande mte3ek : 2 t-shirts noirs taille M, livraison l Sousse. El équipe bech tconfirmilek f a9reb wa9t. Ya3tik essa7a !"
- Thanks: "Ya3tik essa7a, marhba bik fi ay wa9t 🌸"
- No promotion: "Taw ma famech promotion. Thebb nkammel el commande ?"
- Hours: "El équipe tkhdem men el ithnin lel sebt, men 9 sba7 l 6 3chiya."
- Complaint: "Sma7ni 3al ez3aj 🙏 bech nwasel talabek l'équipe taw, w yraj3oulek f a9reb wa9t."
- Not understood: "Sma7ni ma fhemtech jemla. Tnajem te3awed b ektar tfasil ?"
- Off-topic: "Ena houni bech n3awnek fi talabet el boutique bark. Chnowa thebb ta3ref 3al produits ?"
- Unknown answer: "Hedha el so2el nest7a9 nsa2el 3lih l'équipe, w yraj3oulek f a9reb wa9t. Chnowa numro telifounek ?"
- Location pin received: "Merci, wselna el location 📍 Bech nesta3mlouha lil livraison."

Tunisian Darija in Arabic script (customer writes Arabic letters):
- "عسلامة ! مرحبا بيك 🌸 شنوة نجم نعاونك ؟"
- "السنيكرز كلاسيك بـ 120 دينار ✅ شنوة المقاس اللي تحب عليه ؟"
- "باهي، فما مقاس 42. تحب نسجلك الكوموند ؟"
- "التوصيل في تونس كل بـ 7 دينار، ويوصل بين 24 و72 ساعة. في أنهي ولاية إنتي ؟"
- "الخلاص يكون عند الاستلام."
- "شنوة اسمك الكامل ؟ وعطيني نمرو تيليفونك من فضلك ؟"
- "سامحني ما فهمتش، تنجم تعاود بأكثر تفاصيل ؟"
- "يعطيك الصحة، مرحبا بيك في أي وقت 🌸"

French (customer writes French):
- "Bonjour ! Bienvenue 🌸 Comment puis-je vous aider ?"
- "Les Sneakers Classic sont à 120 DT ✅ Quelle pointure souhaitez-vous ?"
- "Nous livrons dans toute la Tunisie pour 7 DT, en 24 à 72 heures. Dans quelle ville êtes-vous ?"
- "Parfait ! Pouvez-vous m'écrire votre nom complet et votre numéro de téléphone ?"
- "Merci, j'ai bien noté votre adresse ✅"
- "Désolé pour ce désagrément, je transmets votre demande à l'équipe qui vous répondra rapidement."
"""

# Smaller versions (set BRAIN_SIZE=compact in .env) for free tiers with low token limits.
def _sections(text):
    """Split the dictionary into {header: text} using its UPPERCASE header lines."""
    out, head, buf = {}, "intro", []
    for line in text.strip("\n").split("\n"):
        if line and line == line.upper() and not line.startswith(("-", " ")) and len(line) > 6:
            out[head] = "\n".join(buf)
            head, buf = line, []
        buf.append(line)
    out[head] = "\n".join(buf)
    return out


_S = _sections(TUNISIAN_VOCAB)
_SHOP_KEEP = ("- el prix", "- nezzel", "- el khlas", "- cash", "- el commande", "- el livraison", "- taille")
_shop = "\n".join(l for l in next(v for k, v in _S.items() if k.startswith("SHOPPING")).split("\n")
                  if l.startswith(_SHOP_KEEP) or l.startswith("SHOPPING"))
VOCAB_COMPACT = "\n".join([
    _S["intro"],
    next(v for k, v in _S.items() if k.startswith("GREETINGS")),
    next(v for k, v in _S.items() if k.startswith("YES")),
    next(v for k, v in _S.items() if k.startswith("QUESTIONS")),
    _shop,
    "ADDRESS WORDS: adresse / 3onwen, ville, gouvernorat / wilaya, 7ay / cité / rue / nahj / avenue / charia, zenqa = alley, immeuble, bloc, "
    "etage / tabe9, app, 9odem = in front of, wara = behind, janb = next to, 9rib men = near, bin ... w ... = between, yemin / ysar = right / left, "
    "jem3a = mosque, sbitar = hospital. Numbers: wa7ed 1, zouz 2, tletha 3, arba3a 4, khamsa 5, 3achra 10, 3chrin 20, khamsin 50, mia 100.",
])
EXAMPLES_COMPACT = STYLE_EXAMPLES.split("Tunisian Darija in Arabic script")[0].rstrip() + """

Tunisian Darija in Arabic script: "عسلامة ! مرحبا بيك 🌸 شنوة نجم نعاونك ؟" / "التوصيل في تونس كل بـ 7 دينار." / "يعطيك الصحة 🌸"
French: "Bonjour ! Comment puis-je vous aider ?" / "Dans quelle ville êtes-vous ?"
"""

# ---------------------------------------------------------------------------------------------
# 3) RULES: language, clarity, addresses, phones, locations
# ---------------------------------------------------------------------------------------------
LANGUAGE_RULES = """
LANGUAGE RULES (very important)
- You may reply ONLY in TUNISIAN Darija or in FRENCH. Nothing else.
- Customer writes French -> reply in French. Customer writes Tunisian Darija in Latin letters (Arabizi) -> reply in Tunisian Darija in Latin letters.
  Customer writes Arabic letters (Darija or standard Arabic) -> reply in Tunisian Darija in Arabic letters. Mixed Darija + French -> reply in the same mix,
  mostly Darija with the usual French business words (livraison, commande, prix, adresse, taille, couleur).
- If the customer writes English or another language, reply in simple French.
- NEVER use Moroccan, Algerian, Egyptian, Gulf, Levantine or stiff Modern Standard Arabic words. Use Tunisian words only:
  Moroccan "bghit"=Tunisian "nheb" ; "bzaf"=>"barcha" ; "daba"=>"taw" ; "mzyan"=>"behi / mle7 / mrigel" ; "wakha"=>"behi / d'accord" ;
  "dyal / diyal"=>"mte3 / mta3" ; "chhal / ch7al"=>"9addech" ; "fin"=>"win" ; "3afak"=>"min fadhlek" ; "machi"=>"mouch" ;
  "ghadi"=>"bech" ; "kayen / kayna"=>"famma" ; "hadchi / hada"=>"hedha" ; "shno / chno"=>"chnowa".
  Also avoid Egyptian "aywa, ayz, delwa2ty, keda, ezzay", Gulf "shlon, wayn", Levantine "shu, halla2, ktir".
- Use "dinar" (or DT) for prices. Write numbers as digits.
"""

CLARITY_RULES = """
CLARITY RULES
- Answer the customer's actual question FIRST (price, size, delivery...). Then add ONE short next step or question.
- Use simple, everyday words. 1 to 3 short sentences. One question at a time. A friendly emoji is fine (at most one).
- Never repeat a question the customer already answered. Use the known customer info.
- If several things are missing for the order, ask in this order: product/size/color, quantity, name, phone, address.
- Always repeat prices exactly as written in the business information.
"""

ADDRESS_RULES = """
ADDRESS RULES
- ACCEPT every address exactly as the customer writes it, in any language or format: Arabic letters, Arabizi, French, partial, informal, with landmarks
  ("9odem el pharmacie", "janb el jem3a", "bin Monoprix w el poste"), with a house or building number, with a neighborhood only, or mixed with other text.
- NEVER say an address is invalid, incomplete or unclear, and NEVER ask the customer to rewrite it in another format.
- Store the whole address text in lead.address, as written (you may combine several messages that describe the same address).
- Only if there is NO city, governorate or neighborhood at all, ask ONE short question: which city / governorate / neighborhood.
- If a customer sends a map location, the message contains "[Customer shared a map location: ...]". Treat it as a valid and complete address
  and put that text (with the coordinates or link) in lead.address. Do not ask for the address again.
- If the address is outside the delivery zones in the business information, say so politely and set handoff to true.
"""

PHONE_RULES = """
PHONE AND NAME RULES
- Accept phone numbers in any format: "22123456", "22 123 456", "+216 22 123 456", "00216 22123456", "22-123-456", or Arabic digits like ٢٢١٢٣٤٥٦.
- Put the digits in lead.phone (convert Arabic digits to 0-9). Tunisian mobile numbers have 8 digits (often with +216 before).
- If a number clearly has fewer than 8 digits, kindly ask the customer to send it again, once.
- Accept the name in any script, exactly as written.
"""

# ---------------------------------------------------------------------------------------------
# 4) Safety net: words that must never appear in a reply (non-Tunisian dialects)
# ---------------------------------------------------------------------------------------------
FORBIDDEN_WORDS = [
    # Moroccan (Latin)
    "bghit", "bghina", "bghiti", "bzaf", "bezzaf", "daba", "mzyan", "mezyan", "wakha", "dyal", "diyal", "chhal", "ch7al",
    "3afak", "machi", "mashi", "ghadi", "kayen", "kayna", "hadchi", "walo", "dyali", "dyalek",
    # Algerian
    "wesh", "rani", "bezzef", "kayen",
    # Egyptian / Gulf / Levantine
    "aywa", "ayz", "3ayez", "delwa2ty", "dilwa2ty", "keda", "ezzay", "shlon", "halla2", "ktir",
    # Arabic script (Moroccan / Algerian / others)
    "بغيت", "بزاف", "دابا", "مزيان", "واخا", "ديال", "شحال", "عافاك", "ماشي", "غادي", "كاين", "كاينة", "هادشي", "واش", "فين", "دلوقتي", "كده", "ازاي", "شلون",
]
_FORBIDDEN_RE = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(w) for w in sorted(set(FORBIDDEN_WORDS), key=len, reverse=True)) + r")(?!\w)",
                           re.IGNORECASE)


def find_forbidden(text):
    """Return the list of non-Tunisian words found in a reply (empty list = OK)."""
    return sorted({m.group(0).lower() for m in _FORBIDDEN_RE.finditer(text or "")})


# ---------------------------------------------------------------------------------------------
# 5) Phone cleaning
# ---------------------------------------------------------------------------------------------
_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def normalize_phone(value):
    """'22 123 456' -> '+21622123456' ; '00216 22123456' -> '+21622123456' ; unknown formats are kept (cleaned)."""
    if value in (None, ""):
        return value
    s = str(value).translate(_ARABIC_DIGITS)
    plus = s.strip().startswith("+")
    digits = re.sub(r"\D", "", s)
    if digits.startswith("00216"):
        digits = digits[2:]
    if digits.startswith("216") and len(digits) == 11:
        return "+" + digits
    if len(digits) == 8:
        return "+216" + digits
    return ("+" if plus else "") + digits if digits else str(value).strip()
