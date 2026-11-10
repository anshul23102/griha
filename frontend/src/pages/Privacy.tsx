import { Link } from 'react-router-dom'
import { Board, Notice, Sheet } from '../components/kit'
import { useI18n } from '../i18n'

// Privacy notice written to the Digital Personal Data Protection Rules, 2025 (G.S.R. 846(E), 13 Nov 2025): rule 3 (itemised data, specific purpose,
// how to withdraw consent, how to exercise rights, how to complain to the Board), rule 9 (contact), rule 14 (rights, 90 days) and the
// NBFC KYC Directions 2025 (paras 47, 61). Rules 3, 6 to 16 start on 13 May 2027; we follow them now.
const C = {
  en: {
    title: 'Privacy notice', hi: 'गोपनीयता सूचना',
    data: ['Name, date of birth, PAN, the last four digits of Aadhaar (the full number is never stored), mobile number, city and pincode',
      'Your loan request: product, amount, tenure, and your declared income and employment',
      'Bank statement transactions (read from a PDF you upload or from Account Aggregator data)',
      'Credit bureau report: score, delinquencies, existing obligations, enquiries',
      'KYC results: whether PAN and Aadhaar e-KYC were verified, and the outcome of identity screening',
      'Property details: address, declared value, title, approvals and valuation reports',
      'Your consent record and any request you make about your data'],
    h1: 'What we collect', h2: 'Why we collect it',
    why: 'Only to assess this one loan application: to verify who you are, estimate your income and ability to repay, assess the property, check for fraud and legal restrictions, decide, and tell you the result. It is not used for marketing or cross-selling, and it is not shared except where the law requires (NBFC KYC Directions 2025 para 61).',
    h3: 'How it is protected', prot: 'Each case is encrypted with its own key. The case is opened only with the private link we give you or by an officer who is logged in. Every access and decision is written to a tamper-evident log.',
    h4: 'How long we keep it', keep: 'Where the KYC Directions apply, identification and transaction records must be kept for at least five years (para 47), and logs of processing for at least one year (DPDP Rules, rules 6 and 8). Outside those duties your data is erased when you ask. A request made earlier is recorded, answered, and carried out on the first date the law allows.',
    h5: 'Your rights and how to use them', rights: 'You can withdraw consent (as easily as you gave it), ask to see, correct or erase your data, and nominate another person to act for you. Use the buttons on your case page. We answer within 90 days (rule 14(3)). A withdrawal stops all further processing of your case at once.',
    h6: 'Complaints', comp: 'First write to the lender\'s grievance officer shown on your decision letter. If you are not satisfied you can complain to the Data Protection Board of India (established 14 November 2025, G.S.R. 844(E)). For lending matters the RBI complaint route in the key facts statement also applies.',
    h7: 'Who to contact', contact: 'The lender must name its Data Protection Officer or a contact person here (DPDP Rules, rule 9). This demonstration does not have one: set it before real use.',
    note: 'The notice and safeguard rules of the DPDP Rules 2025 come into force on 13 May 2027. This system follows them already. This is not legal advice.',
    back: 'Back',
  },
  hi: {
    title: 'गोपनीयता सूचना', hi: '',
    data: ['नाम, जन्म तिथि, PAN, आधार के अंतिम चार अंक (पूरा नंबर कभी नहीं रखा जाता), मोबाइल नंबर, शहर और पिनकोड',
      'आपका ऋण अनुरोध: उत्पाद, राशि, अवधि, और घोषित आय व रोज़गार',
      'बैंक स्टेटमेंट के लेन-देन (आपके अपलोड किए PDF या Account Aggregator डेटा से)',
      'क्रेडिट ब्यूरो रिपोर्ट: स्कोर, चूक, मौजूदा देनदारियाँ, पूछताछ',
      'KYC परिणाम: PAN और आधार e-KYC सत्यापित हुए या नहीं, और पहचान स्क्रीनिंग का नतीजा',
      'संपत्ति का विवरण: पता, घोषित मूल्य, स्वामित्व, मंज़ूरियाँ और मूल्यांकन रिपोर्ट',
      'आपकी सहमति का रिकॉर्ड और अपने डेटा के बारे में आपका कोई भी अनुरोध'],
    h1: 'हम क्या एकत्र करते हैं', h2: 'क्यों एकत्र करते हैं',
    why: 'केवल इसी एक ऋण आवेदन का आकलन करने के लिए: आपकी पहचान जाँचने, आय और चुकाने की क्षमता आँकने, संपत्ति परखने, धोखाधड़ी और कानूनी रोक की जाँच करने, निर्णय लेने और आपको नतीजा बताने के लिए। इसका उपयोग विपणन या क्रॉस-सेलिंग में नहीं होता, और कानून की माँग के सिवा साझा नहीं किया जाता (NBFC KYC निर्देश 2025, पैरा 61)।',
    h3: 'यह कैसे सुरक्षित है', prot: 'हर मामला अपनी अलग कुंजी से एन्क्रिप्ट होता है। मामला केवल आपके निजी लिंक से या लॉग-इन किए अधिकारी से खुलता है। हर पहुँच और निर्णय छेड़छाड़-प्रमाण लॉग में दर्ज होता है।',
    h4: 'कितने समय तक रखा जाता है', keep: 'जहाँ KYC निर्देश लागू हैं, पहचान और लेन-देन के रिकॉर्ड कम से कम पाँच वर्ष (पैरा 47) और प्रसंस्करण के लॉग कम से कम एक वर्ष रखने होते हैं (DPDP नियम, नियम 6 और 8)। इन दायित्वों के बाहर आपके कहने पर डेटा मिटा दिया जाता है। पहले किया गया अनुरोध दर्ज होता है, उसका उत्तर दिया जाता है, और कानून जिस पहली तारीख की अनुमति दे उस दिन पूरा किया जाता है।',
    h5: 'आपके अधिकार और उनका उपयोग', rights: 'आप सहमति वापस ले सकते हैं (उतनी ही आसानी से जितनी से दी थी), अपना डेटा देखने, सुधारने या मिटाने को कह सकते हैं, और अपनी ओर से किसी को नामित कर सकते हैं। अपने मामले के पृष्ठ पर दिए बटन का उपयोग करें। हम 90 दिनों में उत्तर देते हैं (नियम 14(3))। वापसी से आपके मामले की आगे की सारी प्रक्रिया तुरंत रुक जाती है।',
    h6: 'शिकायतें', comp: 'पहले अपने निर्णय पत्र में दिए ऋणदाता के शिकायत अधिकारी को लिखें। संतुष्ट न हों तो भारतीय डेटा संरक्षण बोर्ड (स्थापित 14 नवंबर 2025, G.S.R. 844(E)) में शिकायत कर सकते हैं। ऋण संबंधी मामलों में मुख्य तथ्य विवरण में दिया RBI शिकायत मार्ग भी लागू है।',
    h7: 'किससे संपर्क करें', contact: 'ऋणदाता को यहाँ अपने डेटा संरक्षण अधिकारी या संपर्क व्यक्ति का नाम देना होगा (DPDP नियम, नियम 9)। इस प्रदर्शन में कोई नहीं है: वास्तविक उपयोग से पहले तय करें।',
    note: 'DPDP नियम 2025 के सूचना और सुरक्षा उपाय संबंधी नियम 13 मई 2027 से लागू होंगे। यह प्रणाली उन्हें अभी से मानती है। यह कानूनी सलाह नहीं है।',
    back: 'वापस',
  },
}

const Sec = ({ h, children }: { h: string; children: React.ReactNode }) => <Sheet title={h}><div className="px-5 py-4 max-w-[75ch]">{children}</div></Sheet>

export default function Privacy() {
  const { lang } = useI18n()
  const x = C[lang] ?? C.en
  return (
    <div className="flex flex-col gap-6">
      <Board hi="गोपनीयता सूचना" en="Privacy notice"><p className="m-0 mt-2">DPDP Rules 2025 · NBFC KYC Directions 2025</p></Board>
      <Sec h={x.h1}><ul className="m-0 pl-5 grid gap-1.5">{x.data.map((d, i) => <li key={i}>{d}</li>)}</ul></Sec>
      <Sec h={x.h2}><p className="m-0">{x.why}</p></Sec>
      <Sec h={x.h3}><p className="m-0">{x.prot}</p></Sec>
      <Sec h={x.h4}><p className="m-0">{x.keep}</p></Sec>
      <Sec h={x.h5}><p className="m-0">{x.rights}</p></Sec>
      <Sec h={x.h6}><p className="m-0">{x.comp}</p></Sec>
      <Sec h={x.h7}><p className="m-0">{x.contact}</p></Sec>
      <Notice tone="info">{x.note}</Notice>
      <p className="m-0"><Link to="/apply" className="underline">{x.back}</Link></p>
    </div>
  )
}
