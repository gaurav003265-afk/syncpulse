# Escalation Coverage Matrix

**Standard**: Talent AP Mega Hackathon 2026 — Problem H5 (Offline Frontline Health-Worker Companion)  
**Rule Source of Truth**: [`data/escalation_rules.json`](file:///c:/Users/gaura/Downloads/sync%20pluse/data/escalation_rules.json)  
**Corpus Root**: [`data/synthetic_corpus/`](file:///c:/Users/gaura/Downloads/sync%20pluse/data/synthetic_corpus/)  
**Recall Requirement**: **100% on all emergency danger signs (hard gate)**.

---

## 1. Pregnancy & Antenatal Danger Signs

| Danger Sign | Rule ID | Corpus Document & Section | Action Protocol | Supported Dialects / Synonyms |
| :--- | :--- | :--- | :--- | :--- |
| **Vaginal Bleeding in Pregnancy** (Any trimester, APH) | `ESC-MAT-01` | `DOC-DANG-03#DANG-01` | Immediate referral to FRU/District Hospital via 108/102. Flat rest, feet elevated. | English (`bleeding in pregnancy`, `APH`), Telugu (`రక్తస్రావం`, `raktham vasthondi`), Hindi (`खून निकलना`, `khoon gir raha hai`). |
| **Eclampsia / Convulsions / Seizures** | `ESC-MAT-02` | `DOC-DANG-03#DANG-01` | Immediate referral to FRU. Left lateral tilt, clear airway, do not insert tongue depressor. | English (`eclampsia`, `fits`), Telugu (`ఫిట్స్`, `జెన్ని`, `murccha`), Hindi (`दौरे`, `jhatke`, `mirgi`). |
| **Severe Headache + Blurred Vision** (Impending Eclampsia) | `ESC-MAT-03` | `DOC-DANG-03#DANG-01` | Immediate referral to FRU for MgSO4 evaluation and BP control. | English (`severe headache blurred vision`), Telugu (`తీవ్రమైన తలనొప్పి`, `thalanoppi choopu theda`), Hindi (`तीव्र सिरदर्द`, `dhundhla`). |
| **Leaking Amniotic Fluid / PROM** | `ESC-MAT-04` | `DOC-DANG-03#DANG-01` | Immediate referral. Risk of cord prolapse and chorioamnionitis. Clean pad. | English (`water breaking`, `amniotic fluid leak`), Telugu (`నీళ్లు కారడం`, `neellu karuthunnayi`), Hindi (`पानी छूटना`, `pani gir raha`). |
| **Reduced / Absent Fetal Movement** | `ESC-MAT-05` | `DOC-DANG-03#DANG-01` | Immediate referral for fetal Doppler / emergency ultrasound / NST. | English (`baby not moving`, `reduced fetal movement`), Telugu (`బిడ్డ కదలడం లేదు`, `bidda kadalika`), Hindi (`बच्चा हिल नहीं रहा`). |
| **Severe Abdominal Pain** | `ESC-MAT-06` | `DOC-DANG-03#DANG-01` | Immediate referral. Suspect placental abruption, uterine rupture, or ectopic. | English (`severe abdominal pain`), Telugu (`తీవ్రమైన కడుపు నొప్పి`, `theevramaina kadupu noppi`), Hindi (`पेट में तेज दर्द`). |

---

## 2. Intrapartum & Postpartum Danger Signs

| Danger Sign | Rule ID | Corpus Document & Section | Action Protocol | Supported Dialects / Synonyms |
| :--- | :--- | :--- | :--- | :--- |
| **Prolonged or Obstructed Labor / Cord Prolapse** | `ESC-INTRA-01` | `DOC-DANG-03#DANG-02` | Immediate transfer to CEmONC facility. Knee-chest position if cord prolapses. | English (`prolonged labor > 12h`, `cord prolapse`), Telugu (`ప్రసవంలో అడ్డంకి`, `prasavam 12 gantalu`), Hindi (`प्रसव में रुकावट`). |
| **Postpartum Hemorrhage (PPH)** | `ESC-POST-01` | `DOC-DANG-03#DANG-03` | Immediate referral to FRU. Uterine massage, feet elevated, IV access. | English (`PPH`, `soaking 2 pads in 1 hour`), Telugu (`ప్రసవానంతర రక్తస్రావం`, `delivery tharvatha raktham`), Hindi (`प्रसवोत्तर रक्तस्राव`). |
| **Puerperal Sepsis (Foul Lochia + High Fever)** | `ESC-POST-02` | `DOC-DANG-03#DANG-03` | Immediate referral to CHC/hospital for IV antibiotics. Danger of septic shock. | English (`foul lochia fever`, `puerperal sepsis`), Telugu (`దుర్వాసనతో కూడిన స్రావం`, `kampu vasana jwaram`), Hindi (`दुर्गंधयुक्त स्राव`). |

---

## 3. Sick Newborn (0–28 Days) Danger Signs

| Danger Sign | Rule ID | Corpus Document & Section | Action Protocol | Supported Dialects / Synonyms |
| :--- | :--- | :--- | :--- | :--- |
| **Inability to Feed / Poor Sucking** | `ESC-NEO-01` | `DOC-DANG-03#DANG-04` | Immediate referral to Special Newborn Care Unit (SNCU). Keep warm via KMC. | English (`baby not feeding`, `unable to suck`), Telugu (`పాలు తాగలేకపోవడం`, `palu chekatledu`), Hindi (`दूध नहीं पी रहा`). |
| **Fast Breathing (Tachypnea >= 60 bpm)** | `ESC-NEO-02` | `DOC-DANG-03#DANG-04` | Immediate referral to SNCU. Full 60s count. Numeric parser detects `>=60`. | English (`fast breathing newborn`, `rr >= 60`), Telugu (`వేగంగా శ్వాస`, `aayasam baby`), Hindi (`तेज सांस शिशु`). |
| **Severe Chest Indrawing** | `ESC-NEO-03` | `DOC-DANG-03#DANG-04` | Immediate referral to SNCU. Sign of severe pneumonia / respiratory failure. | English (`chest indrawing`, `subcostal retraction`), Telugu (`ఛాతీ లోపలికి లాగడం`, `rommu lopaliki povatam`), Hindi (`छाती अंदर धंसना`). |
| **Newborn Convulsions / Twitching** | `ESC-NEO-04` | `DOC-DANG-03#DANG-04` | Immediate referral to SNCU. Clear mouth, maintain warmth, do not force water. | English (`newborn convulsions`, `baby fits`), Telugu (`చిన్నారికి ఫిట్స్`, `baby janni`), Hindi (`नवजात को झटके`, `shishu daure`). |
| **Severe Jaundice (Day 1 or Palms/Soles)** | `ESC-NEO-05` | `DOC-DANG-03#DANG-04` | Immediate referral to SNCU. Phototherapy / exchange transfusion evaluation. | English (`jaundice day 1`, `yellow palms and soles`), Telugu (`పసిరికలు`, `arachethulu pasupu`), Hindi (`पीलिया`, `peeliya hatheli talwe`). |
| **Severe Hypothermia (<35.5°C) or Fever (>=37.5°C)** | `ESC-NEO-06` | `DOC-DANG-03#DANG-04` | Immediate referral to SNCU. Immediate skin-to-skin KMC for hypothermia. | English (`baby cold to touch`, `hypothermia`), Telugu (`చల్లబడటం`, `challabadi poyindi`), Hindi (`ठंडा पड़ जाना`). |
| **Umbilical Redness Spreading or Pus** | `ESC-NEO-07` | `DOC-DANG-03#DANG-04` | Immediate referral for systemic IV antibiotics. Never apply cow dung/ash. | English (`umbilical pus`, `omphalitis`), Telugu (`బొడ్డు చీము`, `boddu cheemu`), Hindi (`नाभि से मवाद`, `nabhi lal`). |
| **Lethargy, Floppiness, Cyanosis** | `ESC-NEO-08` | `DOC-DANG-03#DANG-04` | Immediate referral to SNCU. Keep airway open, warm, prevent suffocation. | English (`baby floppy`, `unconscious`, `blue lips`), Telugu (`అపస్మారక స్థితి`, `spruha ledhu`, `neela padadam`), Hindi (`बेहोशी`, `neela padna`). |

---

## 4. Child Malnutrition Danger Signs

| Danger Sign | Rule ID | Corpus Document & Section | Action Protocol | Supported Dialects / Synonyms |
| :--- | :--- | :--- | :--- | :--- |
| **Bilateral Pitting Edema (Kwashiorkor)** | `ESC-NUT-01` | `DOC-NUT-04#NUT-02` | Immediate referral to Nutrition Rehabilitation Centre (NRC). Absolute emergency. | English (`bilateral pitting edema`, `edema both feet`), Telugu (`రెండు కాళ్ల వాపు`, `kaalla vaapu`), Hindi (`दोनों पैरों में सूजन`, `gaddha`). |
| **SAM with Complications / Failed Appetite** | `ESC-NUT-02` | `DOC-NUT-04#NUT-04` | Immediate referral to NRC. Keep child warm. Numeric parser detects `MUAC < 115`. | English (`failed appetite test`, `sam with fever`, `muac < 115`), Telugu (`ఆకలి పరీక్ష ఫెయిల్`), Hindi (`भूख परीक्षण विफल`). |

---

## 5. Non-Communicable Diseases (NCD) Emergencies

| Danger Sign | Rule ID | Corpus Document & Section | Action Protocol | Supported Dialects / Synonyms |
| :--- | :--- | :--- | :--- | :--- |
| **Hypertensive Crisis (BP >= 180/110 mmHg)** | `ESC-NCD-01` | `DOC-NCD-05#NCD-02` | Immediate referral to CHC/District Hospital. Seated rest, call 108. | English (`hypertensive crisis`, `bp >= 180/110`), Telugu (`బీపీ 180 దాటింది`), Hindi (`रक्तचाप 180 से ज्यादा`). |
| **High BP with Stroke / MI Red Flags** | `ESC-NCD-02` | `DOC-NCD-05#NCD-02` | Immediate referral. Suspected Stroke or Acute MI. Call 108 immediately. | English (`high bp chest pain`, `slurred speech`, `stroke`), Telugu (`గుండెల్లో నొప్పి బీపీ`, `పక్షవాతం`), Hindi (`सीने में दर्द बीपी`, `लकवा`). |
| **Severe Hypoglycemia Emergency** | `ESC-NCD-03` | `DOC-NCD-05#NCD-04` | Sugar/jaggery if conscious. If drowsy/unconscious, call 108 for IV dextrose. | English (`sugar < 70 unconscious`, `hypoglycemia`), Telugu (`షుగర్ పడిపోయి స్పృహ లేదు`), Hindi (`शुगर गिरना बेहोशी`). |

---

## 6. Diarrhea, Dehydration & Fever Red Flags

| Danger Sign | Rule ID | Corpus Document & Section | Action Protocol | Supported Dialects / Synonyms |
| :--- | :--- | :--- | :--- | :--- |
| **Severe Dehydration** | `ESC-ORS-01` | `DOC-ORS-06#ORS-01` | Immediate referral for IV Ringer's Lactate resuscitation. ORS sips en route. | English (`severe dehydration`, `skin pinch > 2s`), Telugu (`తీవ్రమైన నిర్జలీకరణ`, `చర్మం మడత`), Hindi (`गंभीर निर्जलीकरण`). |
| **Dysentery or Diarrhea >= 14 Days** | `ESC-ORS-02` | `DOC-ORS-06#ORS-04` | Immediate referral to PHC/CHC Medical Officer. | English (`blood in stool`, `persistent diarrhea 14 days`), Telugu (`రక్త విరేచనాలు`), Hindi (`मल में खून`, `दस्त 14 दिन`). |
| **Fever with Stiff Neck (Meningitis)** | `ESC-FEV-01` | `DOC-ORS-06#ORS-05` | Immediate hospital referral. Bacterial meningitis suspicion. | English (`fever stiff neck`, `unable to bend neck`), Telugu (`మెడ పట్టేయడం జ్వరం`), Hindi (`बुखार गर्दन अकड़ना`). |
| **Fever with Convulsions / Delirium** | `ESC-FEV-02` | `DOC-ORS-06#ORS-05` | Immediate CHC/hospital referral. Status epilepticus or cerebral infection risk. | English (`fever convulsions`, `febrile seizures`), Telugu (`జ్వరం ఫిట్స్`, `జ్వరం స్పృహ తప్పడం`), Hindi (`बुखार में दौरे`). |
| **Fever with Petechial Rash / Bleeding** | `ESC-FEV-03` | `DOC-ORS-06#ORS-05` | Immediate hospital referral. Suspected Severe Dengue / Purpura. No aspirin. | English (`fever petechial rash`, `bleeding gums`), Telugu (`జ్వరం ఎరుపు మచ్చలు`), Hindi (`बुखार लाल चकत्ते`). |
| **Prolonged Fever (> 7 Days)** | `ESC-FEV-04` | `DOC-ORS-06#ORS-05` | Immediate referral to PHC for lab workup (Malaria/Typhoid/TB). | English (`fever > 7 days`, `fever for 10 days`), Telugu (`జ్వరం 7 రోజులు దాటింది`), Hindi (`7 दिन से ज्यादा बुखार`). |

---

## Zero-Gap Guarantee
Every single danger sign explicitly documented in the protocol corpus maps to at least one rule ID in `data/escalation_rules.json`. The rules engine executes as Step 1 on raw query text before any model retrieval or scoring can occur.
