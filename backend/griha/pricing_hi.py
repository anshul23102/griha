"""Hindi version of the Key Facts Statement (RBC Directions 2025 para 29: the statement must be in a language the borrower understands).

It mirrors pricing.annex_i and pricing.build_kfs()["other_disclosures"] item for item: same numbering, same ids, same numbers. Only the words are Hindi.
The Hindi was written for this prototype and has NOT been reviewed by a legal translator. A lender must have it reviewed before use.
"""
from __future__ import annotations

from . import config
from .pricing import apr, rate_shock

L = "ऋणदाता बताएगा"


def annex_i_hi(principal: float, rate: float, n: int, product: str, fee: int, pay: float) -> dict:
    apr_pct = round(apr(principal, rate, n, fee) * 100, 2)
    shock = rate_shock(principal, rate, n)
    return {
        "source": "RBI (NBFC - उत्तरदायी व्यवसाय आचरण) निर्देश, 2025, अनुलग्नक I और पैरा 29",
        "part1": [
            {"no": 1, "item": "ऋण प्रस्ताव / खाता संख्या और ऋण का प्रकार", "value": "गृह ऋण" if product == "HL" else "संपत्ति के बदले ऋण"},
            {"no": 2, "item": "स्वीकृत ऋण राशि", "value": f"₹{round(principal):,}"},
            {"no": 3, "item": "राशि जारी करने की अनुसूची", "value": L + " (100% एकमुश्त या चरणों में, और अनुबंध का खंड)", "lender_to_set": True},
            {"no": 4, "item": "ऋण अवधि", "value": f"{n} माह ({n // 12} वर्ष)"},
            {"no": 5, "item": "किस्त का विवरण", "value": f"समान मासिक किस्तें: {n} किस्तें, प्रत्येक ₹{round(pay):,}; चुकौती की शुरुआत: " + L, "lender_to_set": True},
            {"no": 6, "item": "ब्याज दर और प्रकार", "value": f"{round(rate * 100, 2)}% वार्षिक, अस्थिर (फ्लोटिंग)"},
            {"no": 7, "item": "अस्थिर दर का विवरण", "value": {
                "reference_benchmark": "RBI नीतिगत रेपो दर", "benchmark_pct": round(config.REPO_RATE * 100, 2), "spread_pct": round((rate - config.REPO_RATE) * 100, 2),
                "final_rate_pct": round(rate * 100, 2), "reset_periodicity": L + " (माह)", "impact_of_25_bps": shock}},
            {"no": 8, "item": "शुल्क और प्रभार", "value": {
                "payable_to_lender": [{"name": "प्रोसेसिंग शुल्क", "type": "एक बार", "amount": f"₹{fee:,}"}],
                "payable_to_third_party_via_lender": [{"name": "मूल्यांकन शुल्क, बीमा", "type": L, "amount": L}]}, "lender_to_set": True},
            {"no": 9, "item": "वार्षिक प्रतिशत दर (APR)", "value": f"{apr_pct}%"},
            {"no": 10, "item": "आकस्मिक शुल्क", "value": {
                "विलंब पर दंडात्मक शुल्क": L + "। दंडात्मक शुल्क ब्याज दर में नहीं जोड़ा जाता और उस पर ब्याज नहीं लगता",
                "अन्य दंडात्मक शुल्क": L,
                "पूर्व-समापन शुल्क": "शून्य" if product == "HL" else "गैर-व्यावसायिक उद्देश्य के लिए शून्य; व्यावसायिक उद्देश्य के लिए जैसा बताया गया",
                "स्थिर/अस्थिर दर बदलने का शुल्क": L}, "lender_to_set": True},
        ],
        "part2": [
            {"no": 1, "item": "वसूली एजेंटों के बारे में ऋण अनुबंध का खंड", "value": L, "lender_to_set": True},
            {"no": 2, "item": "शिकायत निवारण के बारे में ऋण अनुबंध का खंड", "value": L, "lender_to_set": True},
            {"no": 3, "item": "नोडल शिकायत निवारण अधिकारी का फोन और ईमेल", "value": L, "lender_to_set": True},
            {"no": 4, "item": "ऋण अन्य ऋणदाताओं को हस्तांतरित या प्रतिभूतिकृत हो सकता है", "value": L, "lender_to_set": True},
            {"no": 5, "item": "सह-ऋण या आउटसोर्सिंग व्यवस्था", "value": "लागू नहीं: इस प्रोटोटाइप में कोई सह-ऋणदाता नहीं"},
            {"no": 6, "item": "डिजिटल ऋण: प्रीपेमेंट दंड के बिना विचार-अवधि; वसूली एजेंट LSP", "value": f"{config.COOLING_OFF_DAYS} दिन (उदाहरण के लिए; यह बोर्ड तय करता है)। इस प्रोटोटाइप में कोई ऋण सेवा प्रदाता नहीं"},
        ],
        "apr_sheet": [
            ["स्वीकृत ऋण राशि", f"₹{round(principal):,}"], ["ऋण अवधि", f"{n} माह"], ["समान मासिक किस्त", f"₹{round(pay):,} x {n}"],
            ["ब्याज दर और प्रकार", f"{round(rate * 100, 2)}% अस्थिर"], ["पूरी अवधि का कुल ब्याज", f"₹{round(pay * n - principal):,}"],
            ["शुल्क और प्रभार", f"₹{fee:,} (ऋणदाता को देय)"], ["कुल वितरित शुद्ध राशि", f"₹{round(principal) - fee:,}"],
            ["उधारकर्ता द्वारा देय कुल राशि", f"₹{round(pay * n):,}"],
            ["APR (वितरित शुद्ध राशि पर IRR, घटते शेष पर)", f"{apr_pct}%"],
        ],
        "risk_premium_pct": round((rate - config.BASE_RATE - (0.015 if product == "LAP" else 0.0)) * 100, 2),
    }


def disclosures_hi(principal: float, rate: float, n: int, product: str, fee: int) -> list[dict]:
    a = round(apr(principal, rate, n, fee) * 100, 2)
    repo = round(config.REPO_RATE * 100, 2)
    prem = round((rate - config.BASE_RATE - (0.015 if product == "LAP" else 0.0)) * 100, 2)
    return [
        {"id": "all_in_cost", "label": "कुल लागत", "value": f"APR {a}%, प्रोसेसिंग शुल्क सहित", "basis": "HFC निर्देश 2025 पैरा 132"},
        {"id": "fee_refund", "label": "ऋण स्वीकृत या वितरित न होने पर प्रोसेसिंग शुल्क", "value": "वापसी योग्य राशि ऋणदाता बताएगा। उदाहरण: ऋण वितरित न हो तो पूरा वापस", "basis": "HFC निर्देश 2025 पैरा 131(1) और (2)"},
        {"id": "penal", "label": "भुगतान में देरी पर दंडात्मक शुल्क", "value": "ऋणदाता तय करके बताएगा। उदाहरण: बकाया राशि पर 2% वार्षिक, ब्याज दर में नहीं जोड़ा जाएगा", "basis": "HFC निर्देश 2025 पैरा 131(4); RBC निर्देश 2025 पैरा 30(1), (4), (6): यह दंडात्मक शुल्क है, दंडात्मक ब्याज नहीं; इसका पूँजीकरण नहीं होता; केवल बकाया राशि पर लगता है"},
        {"id": "conversion", "label": "स्थिर और अस्थिर दर के बीच बदलने का शुल्क", "value": "ऋणदाता तय करके बताएगा। उदाहरण: शून्य", "basis": "HFC निर्देश 2025 पैरा 131(5)"},
        {"id": "reset", "label": "ब्याज दर का पुनर्निर्धारण", "value": f"अस्थिर दर बेंचमार्क से जुड़ी है (RBI रेपो {repo}% और ऋणदाता का स्प्रेड); बेंचमार्क बदलने पर यह बदलती है। कितनी बार और आपको कैसे सूचित किया जाएगा, यह ऋणदाता बताएगा", "basis": "HFC निर्देश 2025 पैरा 131(6)"},
        {"id": "rate_basis", "label": "आपकी दर कैसे तय हुई", "value": f"बेंचमार्क (RBI रेपो {repo}%) + ऋणदाता का स्प्रेड {round(config.LENDER_SPREAD * 100, 2)}% + जोखिम प्रीमियम, जो चूक के आकलित जोखिम के साथ बढ़ता है" + (" + संपत्ति के बदले ऋण के लिए 1.5%" if product == "LAP" else "") + f"। आपका जोखिम प्रीमियम {prem}% है", "basis": "RBC निर्देश 2025 पैरा 22 से 24"},
        {"id": "no_other_fees", "label": "यहाँ न लिखे गए शुल्क", "value": "जो शुल्क या प्रभार इस विवरण में नहीं है, वह किसी भी चरण पर आपकी स्पष्ट सहमति के बिना नहीं लिया जा सकता", "basis": "RBC निर्देश 2025 पैरा 29(5)"},
        {"id": "validity", "label": "इस विवरण की वैधता", "value": "दिए जाने के दिन से कम से कम तीन कार्य दिवस। इस अवधि में आप स्वीकार करें तो ऋणदाता इन शर्तों से बँधा है", "basis": "RBC निर्देश 2025 पैरा 29(2)"},
        {"id": "reset_options", "label": "अस्थिर दर बदलने पर आपके विकल्प", "value": "आप अधिक किस्त, लंबी अवधि या दोनों चुन सकते हैं; ऋणदाता दे तो स्थिर दर पर जा सकते हैं; या किसी भी समय पूर्ण या आंशिक पूर्व-भुगतान कर सकते हैं। अवधि बढ़ाने से ऋण राशि कभी नहीं बढ़ेगी (नकारात्मक परिशोधन नहीं)। हर तिमाही आपको मूलधन और ब्याज की वसूली, किस्त, शेष किस्तें और APR का विवरण मिलेगा", "basis": "RBC निर्देश 2025 पैरा 31(1) से (6)"},
        {"id": "terms_change", "label": "ऋणदाता आपके नुकसान की शर्तें बदले तो", "value": "आप 60 दिनों के भीतर बिना किसी अतिरिक्त शुल्क या ब्याज के खाता बंद कर सकते हैं या दूसरे ऋणदाता को ले जा सकते हैं", "basis": "HFC निर्देश 2025 पैरा 137"},
    ]
