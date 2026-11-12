# Hindi text for legal review

**Status: not reviewed.** Written for this prototype, not by a legal translator. The Directions require the Key Facts Statement in a language the borrower understands (RBC Directions 2025 para 29), so a lender must have this checked before use.

## How to sign off
1. Read the glossary, then each pair below. Correct any wording in `backend/griha/pricing_hi.py` (the Key Facts Statement) and `frontend/src/pages/Privacy.tsx` (the privacy notice). Numbers come from the engine and must not be edited here.
2. Keep the legal distinctions the English makes: a penal *charge* is not penal *interest*; "Lender to state" means the lender must fill the item, never us.
3. When done, edit `backend/griha/data/hindi_review.json`: set `reviewed` to `true` and fill `reviewer`, `qualification` and `date`. Only then does the app stop saying the Hindi is unreviewed. A bare `true` is ignored.

A note on sources. The Hindi text of the DPDP Rules is in the Gazette PDF; its text layer uses a legacy font and extracts garbled, so the terms below were read by decoding it. Please compare against the PDF itself. No Hindi text of the RBI Directions was available to us.

## Glossary

| English | Hindi used | Basis |
|---|---|---|
| Data Principal | डेटा प्रिंसिपल | DPDP Rules 2025, Hindi gazette text (G.S.R. 846(E)): the official Hindi text transliterates the term |
| Data Fiduciary | डेटा फिड्यूसरी | DPDP Rules 2025, Hindi gazette text |
| personal data | वैयक्तिक डेटा | DPDP Rules 2025, Hindi gazette text |
| consent / verifiable consent | सहमति / सत्यापन योग्य सहमति | DPDP Rules 2025, Hindi gazette text |
| notice (rule 3) | नोटिस | DPDP Rules 2025, Hindi gazette text |
| Consent Manager | सहमति प्रबंधक | DPDP Rules 2025, Hindi gazette text |
| Data Protection Board | डेटा संरक्षण बोर्ड | DPDP Rules 2025, Hindi gazette text uses "बोर्ड" for the Board |
| Key Facts Statement (KFS) | मुख्य तथ्य विवरण (KFS) | Our choice. No official Hindi text of the RBI Directions was available to us |
| annual percentage rate (APR) | वार्षिक प्रतिशत दर (APR) | Our choice |
| equated monthly instalment | समान मासिक किस्त | Our choice; common banking usage |
| floating rate | फ्लोटिंग (परिवर्ती) दर | Our choice. An earlier draft used "अस्थिर" (unstable), which reads badly, so it was changed |
| benchmark / repo rate | बेंचमार्क / रेपो दर | Our choice |
| spread | स्प्रेड | Our choice |
| penal charges | दंडात्मक शुल्क | Our choice. The Directions distinguish penal charges from penal interest: the reviewer must keep that distinction |
| pre-closure / foreclosure | पूर्व-समापन | Our choice |
| pre-payment | पूर्व-भुगतान | Our choice |
| grievance redressal officer | शिकायत निवारण अधिकारी | Our choice |
| cooling-off period | विचार-अवधि | Our choice |
| negative amortisation | नकारात्मक परिशोधन | Our choice |
| Lender to state | ऋणदाता बताएगा | Placeholder for an item only the lender can know; never filled in by us |

## Key Facts Statement (Annex I) and disclosures

| Item | English | Hindi |
|---|---|---|
| Annex I part1 item 1 | Loan proposal / account number and type of loan: Home loan | ऋण प्रस्ताव / खाता संख्या और ऋण का प्रकार: गृह ऋण |
| Annex I part1 item 2 | Sanctioned loan amount: ₹2,400,000 | स्वीकृत ऋण राशि: ₹2,400,000 |
| Annex I part1 item 3 | Disbursal schedule: Lender to state (100% upfront or in stages, and the clause of the agreement) | राशि जारी करने की अनुसूची: ऋणदाता बताएगा (100% एकमुश्त या चरणों में, और अनुबंध का खंड) |
| Annex I part1 item 4 | Loan term: 240 months (20 years) | ऋण अवधि: 240 माह (20 वर्ष) |
| Annex I part1 item 5 | Instalment details: Equated monthly instalments: 240 of ₹22,450; repayment starts lender to state | किस्त का विवरण: समान मासिक किस्तें: 240 किस्तें, प्रत्येक ₹22,450; चुकौती की शुरुआत: ऋणदाता बताएगा |
| Annex I part1 item 6 | Interest rate and type: 9.55% a year, floating | ब्याज दर और प्रकार: 9.55% वार्षिक, फ्लोटिंग (परिवर्ती) |
| Annex I part1 item 7 | Floating rate details | फ्लोटिंग दर का विवरण |
| Annex I part1 item 8 | Fees and charges | शुल्क और प्रभार |
| Annex I part1 item 9 | Annual percentage rate (APR): 9.69% | वार्षिक प्रतिशत दर (APR): 9.69% |
| Annex I part1 item 10 | Contingent charges | आकस्मिक शुल्क |
| Annex I part2 item 1 | Clause of the loan agreement on recovery agents: Lender to state | वसूली एजेंटों के बारे में ऋण अनुबंध का खंड: ऋणदाता बताएगा |
| Annex I part2 item 2 | Clause of the loan agreement on grievance redressal: Lender to state | शिकायत निवारण के बारे में ऋण अनुबंध का खंड: ऋणदाता बताएगा |
| Annex I part2 item 3 | Phone and email of the nodal grievance officer: Lender to state | नोडल शिकायत निवारण अधिकारी का फोन और ईमेल: ऋणदाता बताएगा |
| Annex I part2 item 4 | Loan may be transferred to other lenders or securitised: Lender to state | ऋण अन्य ऋणदाताओं को हस्तांतरित या प्रतिभूतिकृत हो सकता है: ऋणदाता बताएगा |
| Annex I part2 item 5 | Co-lending or outsourcing arrangement: Not applicable: no co-lender in this prototype | सह-ऋण या आउटसोर्सिंग व्यवस्था: लागू नहीं: इस प्रोटोटाइप में कोई सह-ऋणदाता नहीं |
| Annex I part2 item 6 | Digital loan: cooling-off period without prepayment penalty; recovery-agent LSP: 3 days (illustrative; the Board sets it). No lending service provider in this prototype | डिजिटल ऋण: प्रीपेमेंट दंड के बिना विचार-अवधि; वसूली एजेंट LSP: 3 दिन (उदाहरण के लिए; यह बोर्ड तय करता है)। इस प्रोटोटाइप में कोई ऋण सेवा प्रदाता नहीं |
| Disclosure all_in_cost (HFC Directions 2025 para 132) | All-in cost: APR 9.69% including the processing fee | कुल लागत: APR 9.69%, प्रोसेसिंग शुल्क सहित |
| Disclosure fee_refund (HFC Directions 2025 para 131(1) and (2)) | Processing fee if the loan is not sanctioned or disbursed: Lender to state the refundable amount. Illustrative: refunded in full if the loan is not disbursed | ऋण स्वीकृत या वितरित न होने पर प्रोसेसिंग शुल्क: वापसी योग्य राशि ऋणदाता बताएगा। उदाहरण: ऋण वितरित न हो तो पूरा वापस |
| Disclosure penal (HFC Directions 2025 para 131(4); RBC Directions 2025 para 30(1), (4), (6): a penal charge, never penal interest, no capitalisation, levied only on the overdue amount, uniform whatever the borrower's constitution) | Penal charges for delayed repayment: Lender to set and disclose. Illustrative: 2% a year on the overdue amount, not added to the interest rate | भुगतान में देरी पर दंडात्मक शुल्क: ऋणदाता तय करके बताएगा। उदाहरण: बकाया राशि पर 2% वार्षिक, ब्याज दर में नहीं जोड़ा जाएगा |
| Disclosure conversion (HFC Directions 2025 para 131(5)) | Charges for switching between fixed and floating rate: Lender to set and disclose. Illustrative: nil | स्थिर और फ्लोटिंग दर के बीच बदलने का शुल्क: ऋणदाता तय करके बताएगा। उदाहरण: शून्य |
| Disclosure reset (HFC Directions 2025 para 131(6)) | Interest reset: Floating rate linked to the benchmark (RBI repo 5.5% plus the lender's spread); it changes when the benchmark changes. Lender to state how often and how you are told | ब्याज दर का पुनर्निर्धारण: फ्लोटिंग दर बेंचमार्क से जुड़ी है (RBI रेपो 5.5% और ऋणदाता का स्प्रेड); बेंचमार्क बदलने पर यह बदलती है। कितनी बार और आपको कैसे सूचित किया जाएगा, यह ऋणदाता बताएगा |
| Disclosure rate_basis (RBC Directions 2025 paras 22 to 24) | How your rate was set: Benchmark (RBI repo 5.5%) plus the lender's spread 4.0% plus a risk premium that rises with the assessed risk of default. Your risk premium is 0.05% | आपकी दर कैसे तय हुई: बेंचमार्क (RBI रेपो 5.5%) + ऋणदाता का स्प्रेड 4.0% + जोखिम प्रीमियम, जो चूक के आकलित जोखिम के साथ बढ़ता है। आपका जोखिम प्रीमियम 0.05% है |
| Disclosure no_other_fees (RBC Directions 2025 para 29(5)) | Charges not listed here: No fee or charge that is not in this statement can be levied at any stage without your explicit consent | यहाँ न लिखे गए शुल्क: जो शुल्क या प्रभार इस विवरण में नहीं है, वह किसी भी चरण पर आपकी स्पष्ट सहमति के बिना नहीं लिया जा सकता |
| Disclosure validity (RBC Directions 2025 para 29(2)) | Validity of this statement: At least three working days from the day it is given. If you accept within that time the lender is bound by these terms | इस विवरण की वैधता: दिए जाने के दिन से कम से कम तीन कार्य दिवस। इस अवधि में आप स्वीकार करें तो ऋणदाता इन शर्तों से बँधा है |
| Disclosure reset_options (RBC Directions 2025 para 31(1) to (6)) | When the floating rate is reset: You may choose a higher instalment, a longer tenor or both, switch to a fixed rate if the lender offers it, or prepay in part or in full at any time. Tenor extension will not cause negative amortisation. You get a statement each quarter with principal and interest recovered, instalment, instalments left and APR | फ्लोटिंग दर बदलने पर आपके विकल्प: आप अधिक किस्त, लंबी अवधि या दोनों चुन सकते हैं; ऋणदाता दे तो स्थिर दर पर जा सकते हैं; या किसी भी समय पूर्ण या आंशिक पूर्व-भुगतान कर सकते हैं। अवधि बढ़ाने से ऋण राशि कभी नहीं बढ़ेगी (नकारात्मक परिशोधन नहीं)। हर तिमाही आपको मूलधन और ब्याज की वसूली, किस्त, शेष किस्तें और APR का विवरण मिलेगा |
| Disclosure terms_change (HFC Directions 2025 para 137) | If the lender changes terms to your disadvantage: You may close or switch the account within 60 days without paying any extra charge or interest | ऋणदाता आपके नुकसान की शर्तें बदले तो: आप 60 दिनों के भीतर बिना किसी अतिरिक्त शुल्क या ब्याज के खाता बंद कर सकते हैं या दूसरे ऋणदाता को ले जा सकते हैं |

## Privacy notice (DPDP rule 3)

| Part | English | Hindi |
|---|---|---|
| title | Privacy notice | गोपनीयता सूचना |
| data[0] | Name, date of birth, PAN, the last four digits of Aadhaar (the full number is never stored), mobile number, city and pincode | नाम, जन्म तिथि, PAN, आधार के अंतिम चार अंक (पूरा नंबर कभी नहीं रखा जाता), मोबाइल नंबर, शहर और पिनकोड |
| data[1] | Your loan request: product, amount, tenure, and your declared income and employment | आपका ऋण अनुरोध: उत्पाद, राशि, अवधि, और घोषित आय व रोज़गार |
| data[2] | Bank statement transactions (read from a PDF you upload or from Account Aggregator data) | बैंक स्टेटमेंट के लेन-देन (आपके अपलोड किए PDF या Account Aggregator डेटा से) |
| data[3] | Credit bureau report: score, delinquencies, existing obligations, enquiries | क्रेडिट ब्यूरो रिपोर्ट: स्कोर, चूक, मौजूदा देनदारियाँ, पूछताछ |
| data[4] | KYC results: whether PAN and Aadhaar e-KYC were verified, and the outcome of identity screening | KYC परिणाम: PAN और आधार e-KYC सत्यापित हुए या नहीं, और पहचान स्क्रीनिंग का नतीजा |
| data[5] | Property details: address, declared value, title, approvals and valuation reports | संपत्ति का विवरण: पता, घोषित मूल्य, स्वामित्व, मंज़ूरियाँ और मूल्यांकन रिपोर्ट |
| data[6] | Your consent record and any request you make about your data | आपकी सहमति का रिकॉर्ड और अपने डेटा के बारे में आपका कोई भी अनुरोध |
| h1 | What we collect | हम क्या एकत्र करते हैं |
| h2 | Why we collect it | क्यों एकत्र करते हैं |
| why | Only to assess this one loan application: to verify who you are, estimate your income and ability to repay, assess the property, check for fraud and legal restrictions, decide, and tell you the result. It is not used for marketing or cross-selling, and it is not shared except where the law requires (NBFC KYC Directions 2025 para 61). | केवल इसी एक ऋण आवेदन का आकलन करने के लिए: आपकी पहचान जाँचने, आय और चुकाने की क्षमता आँकने, संपत्ति परखने, धोखाधड़ी और कानूनी रोक की जाँच करने, निर्णय लेने और आपको नतीजा बताने के लिए। इसका उपयोग विपणन या क्रॉस-सेलिंग में नहीं होता, और कानून की माँग के सिवा साझा नहीं किया जाता (NBFC KYC निर्देश 2025, पैरा 61)। |
| h3 | How it is protected | यह कैसे सुरक्षित है |
| prot | Each case is encrypted with its own key. The case is opened only with the private link we give you or by an officer who is logged in. Every access and decision is written to a tamper-evident log. | हर मामला अपनी अलग कुंजी से एन्क्रिप्ट होता है। मामला केवल आपके निजी लिंक से या लॉग-इन किए अधिकारी से खुलता है। हर पहुँच और निर्णय छेड़छाड़-प्रमाण लॉग में दर्ज होता है। |
| h4 | How long we keep it | कितने समय तक रखा जाता है |
| keep | Where the KYC Directions apply, identification and transaction records must be kept for at least five years (para 47), and logs of processing for at least one year (DPDP Rules, rules 6 and 8). Outside those duties your data is erased when you ask. A request made earlier is recorded, answered, and carried out on the first date the law allows. | जहाँ KYC निर्देश लागू हैं, पहचान और लेन-देन के रिकॉर्ड कम से कम पाँच वर्ष (पैरा 47) और प्रसंस्करण के लॉग कम से कम एक वर्ष रखने होते हैं (DPDP नियम, नियम 6 और 8)। इन दायित्वों के बाहर आपके कहने पर डेटा मिटा दिया जाता है। पहले किया गया अनुरोध दर्ज होता है, उसका उत्तर दिया जाता है, और कानून जिस पहली तारीख की अनुमति दे उस दिन पूरा किया जाता है। |
| h5 | Your rights and how to use them | आपके अधिकार और उनका उपयोग |
| rights | You can withdraw consent (as easily as you gave it), ask to see, correct or erase your data, and nominate another person to act for you. Use the buttons on your case page. We answer within 90 days (rule 14(3)). A withdrawal stops all further processing of your case at once. | आप सहमति वापस ले सकते हैं (उतनी ही आसानी से जितनी से दी थी), अपना डेटा देखने, सुधारने या मिटाने को कह सकते हैं, और अपनी ओर से किसी को नामित कर सकते हैं। अपने मामले के पृष्ठ पर दिए बटन का उपयोग करें। हम 90 दिनों में उत्तर देते हैं (नियम 14(3))। वापसी से आपके मामले की आगे की सारी प्रक्रिया तुरंत रुक जाती है। |
| h6 | Complaints | शिकायतें |
| comp | First write to the lender's grievance officer shown on your decision letter. If you are not satisfied you can complain to the Data Protection Board of India (established 14 November 2025, G.S.R. 844(E)). For lending matters the RBI complaint route in the key facts statement also applies. | पहले अपने निर्णय पत्र में दिए ऋणदाता के शिकायत अधिकारी को लिखें। संतुष्ट न हों तो भारतीय डेटा संरक्षण बोर्ड (स्थापित 14 नवंबर 2025, G.S.R. 844(E)) में शिकायत कर सकते हैं। ऋण संबंधी मामलों में मुख्य तथ्य विवरण में दिया RBI शिकायत मार्ग भी लागू है। |
| h7 | Who to contact | किससे संपर्क करें |
| contact | The lender must name its Data Protection Officer or a contact person here (DPDP Rules, rule 9). This demonstration does not have one: set it before real use. | ऋणदाता को यहाँ अपने डेटा संरक्षण अधिकारी या संपर्क व्यक्ति का नाम देना होगा (DPDP नियम, नियम 9)। इस प्रदर्शन में कोई नहीं है: वास्तविक उपयोग से पहले तय करें। |
| note | The notice and safeguard rules of the DPDP Rules 2025 come into force on 13 May 2027. This system follows them already. This is not legal advice. | DPDP नियम 2025 के सूचना और सुरक्षा उपाय संबंधी नियम 13 मई 2027 से लागू होंगे। यह प्रणाली उन्हें अभी से मानती है। यह कानूनी सलाह नहीं है। |
| back | Back | वापस |

## Sign-off

Reviewer: ________________  Qualification: ________________  Date: ____________
