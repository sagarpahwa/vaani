I asked GPT: i am wondering if any such similar public datasets exist already?

and i got this reply:

Yes — **similar public datasets exist**, but not as the exact thing you want.

What exists today is mostly fragmented into:

1. **speaker/person datasets**
2. **speech/transcript corpora**
3. **political/parliamentary speech datasets**
4. **TED/public-talk datasets**
5. **audio/video delivery datasets**
6. **scholarly influence datasets**

What seems **not** to exist publicly is a unified, source-backed database of:

```json
{
  "speaker": "person",
  "speeches": "what they said",
  "delivery": "how they said it",
  "capabilities": "why it worked",
  "audience_effects": "what people felt/did",
  "ethical_risk": "whether influence was responsible",
  "trainable_lessons": "how a learner can practice it"
}
```

That missing layer is the startup opportunity.

## Best existing datasets/sources to build on

| Source / Dataset                                  | What it gives you                                                                                     | Why it matters                                                                                                                                                                                                                       |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Wikidata**                                      | Massive open knowledge graph of people, occupations, countries, dates, aliases, IDs                   | Best starting point for candidate speaker discovery and entity normalization. Wikidata describes itself as a free, open knowledge base readable by humans and machines. ([Wikidata][1])                                              |
| **Pantheon**                                      | Globally memorable biographies, occupations, eras, countries                                          | Useful for “historical notability.” Pantheon says it has data on 85,000+ biographies organized by countries, cities, occupations, and eras. ([Pantheon][2])                                                                          |
| **Pantheon 1.0**                                  | 11,341 manually verified globally famous biographies                                                  | Useful as a high-confidence gold seed set. It includes demographic fields, occupation taxonomy, and popularity measures such as Wikipedia language presence and Historical Popularity Index. ([DSpace][3])                           |
| **Cross-verified Notable People Database**        | Large-scale notable-person database built from Wikipedia and Wikidata                                 | Useful for scaling toward 100k+ candidates. The peer-reviewed dataset combines Wikipedia and Wikidata and cross-verifies information using deduplication. ([Nature][4])                                                              |
| **American Presidency Project**                   | U.S. presidential speeches, remarks, documents, debates, interviews, executive communications         | Very strong source for political and crisis speaking. APP calls itself a non-profit, non-partisan source of presidential documents on the internet. ([The American Presidency Project][5])                                           |
| **Miller Center Presidential Speeches**           | Bulk-download corpus of U.S. presidential speeches                                                    | Good clean corpus for NLP experiments. Miller Center says its presidential-speeches collection has 1,000+ speeches and is available for bulk download. ([Miller Center Data][6])                                                     |
| **GovInfo Compilation of Presidential Documents** | Official U.S. presidential speeches, remarks, news conferences, proclamations, orders, communications | Best official-source layer for recent U.S. presidential material. GovInfo says the collection includes speeches, remarks, news conferences, proclamations, executive orders, and other documents. ([GovInfo][7])                     |
| **UN General Debate Corpus**                      | Speeches by heads of state/world leaders at the UN General Assembly                                   | Excellent global political-speech corpus. The official UNGDC site describes 75+ years of General Debate speeches from member states since 1946. ([Birmingham Global Data Centre][8])                                                 |
| **UN Digital Library GA Debate Dataset**          | Structured speaker metadata for UN General Debate speeches                                            | Very useful for speaker names, states represented, sessions, meeting records, and agenda items; the Jan. 2026 dataset covers 1st–79th sessions. ([Digital Library][9])                                                               |
| **UNGDC GitHub corpus**                           | Plain-text UN General Debate transcripts                                                              | One public GitHub copy describes 10,568 speeches from 1946–2022 plus a speaker/session spreadsheet. ([GitHub][10])                                                                                                                   |
| **ParlSpeech V2**                                 | 6.3 million parliamentary speeches from nine representative democracies                               | Massive corpus for debate, argumentation, ideology, style, and institutional speech analysis. ([Party Facts][11])                                                                                                                    |
| **CLARIN Parliamentary Corpora**                  | Collection/family of parliamentary corpora across languages and countries                             | Good discovery hub for parliamentary speech datasets; CLARIN notes parliamentary proceedings are widely digitized and useful across political science, history, linguistics, sociology, and psychology. ([Clarin][12])               |
| **ParlLawSpeech**                                 | Plenary speeches linked to bills/laws                                                                 | Useful if you want speech-to-policy-impact relationships. The dataset includes chronological plenary speeches by country and links bills, speeches, and law via procedure IDs. ([ParlLawSpeech][13])                                 |
| **TED-LIUM**                                      | TED-talk audio and transcripts for speech recognition                                                 | Useful for voice/audio modeling. TensorFlow Datasets describes TED-LIUM as English TED talks with transcriptions sampled at 16kHz; release 1 has about 118 hours. ([TensorFlow][14])                                                 |
| **TED transcript/metadata datasets**              | TED titles, speakers, occupations, views, tags, transcripts                                           | Useful for public-talk engagement modeling, but licensing must be checked carefully. Kaggle/GitHub mirrors describe datasets with TED talk metadata, transcripts, views, comments, speakers, occupations, and tags. ([Kaggle][15])   |
| **TED rating/prosody research datasets**          | TED viewer ratings, transcripts, audio/prosody features                                               | Useful for learning what correlates with audience response. One study used 2,200+ TED transcripts, audio features, metadata, and about 5.5 million viewer ratings. ([arXiv][16])                                                     |
| **Nobel Prize lectures**                          | Nobel lectures, acceptance speeches, laureate metadata                                                | Strong source for scientific, literary, peace, and moral-authority speaking. Nobel’s site says laureates are required to give a lecture connected to their prize-winning work. ([NobelPrize.org][17])                                |
| **OpenAlex**                                      | Scholarly works, authors, institutions, funders, topics                                               | Useful for scientist/professor authority scoring. OpenAlex describes itself as an open catalog of global research, with hundreds of millions of scholarly works linked to authors, institutions, funders, and more. ([OpenAlex][18]) |
| **SOPHIAS**                                       | Multimodal student oral-presentation dataset                                                          | Useful for training delivery assessment models. SOPHIAS contains recordings of 50 oral presentations by 65 students, with presentation/Q&A structure and multimodal data. ([GitHub][19])                                             |
| **Lecture Presentations Multimodal Dataset**      | Educational lecture videos, slides, speech, multimodal alignment                                      | Useful for teacher/lecturer-style communication analysis. The dataset is designed for understanding multimodality in educational videos. ([GitHub][20])                                                                              |

## My blunt assessment

There is **no single public dataset** that already solves your product.

But there are enough public building blocks to create a very strong proprietary database.

The market gap is not:

```json
{
  "problem": "No speeches exist online"
}
```

The real gap is:

```json
{
  "problem": "No one has converted speeches into a structured, evidence-backed, trainable public-speaking intelligence graph"
}
```

## What you should build from public data

Your database should have four layers:

```json
{
  "layer_1_candidate_universe": [
    "Wikidata",
    "Pantheon",
    "Cross-verified notable people",
    "OpenAlex"
  ],
  "layer_2_speech_corpora": [
    "American Presidency Project",
    "Miller Center",
    "GovInfo",
    "UN General Debate Corpus",
    "ParlSpeech",
    "TED-LIUM",
    "Nobel lectures"
  ],
  "layer_3_analysis_layer": [
    "speaking_capabilities",
    "rhetorical_devices",
    "delivery_profile",
    "audience_effects",
    "ethical_risk_flags",
    "trainable_lessons"
  ],
  "layer_4_product_layer": [
    "speaker archetypes",
    "practice drills",
    "user diagnosis",
    "before-after progress scoring",
    "personalized speaker models"
  ]
}
```

## Best startup strategy

Start with this scope:

```json
{
  "phase_1": {
    "verified_speakers": 1000,
    "candidate_speakers": 100000,
    "deep_speech_profiles": 5000,
    "sources": [
      "Wikidata",
      "Pantheon",
      "American Presidency Project",
      "Miller Center",
      "UN General Debate Corpus",
      "TED-LIUM",
      "Nobel lectures"
    ]
  }
}
```

Do **not** start by trying to deeply profile 100k speakers. That will create a noisy database.

Instead:

```json
{
  "candidate_speakers": "large and broad",
  "verified_speakers": "source-backed and scored",
  "gold_speakers": "deeply analyzed",
  "gold_speeches": "manually reviewed and model-ready"
}
```

Your moat will be the **capability taxonomy + scoring model + evidence graph + training drills**, not the raw public speeches.

[1]: https://www.wikidata.org/wiki/Wikidata%3AMain_Page?utm_source=chatgpt.com "Wikidata"
[2]: https://pantheon.world/?utm_source=chatgpt.com "Pantheon — Explore the Most Memorable People in History | 85,000 ..."
[3]: https://dspace.mit.edu/handle/1721.1/112710?utm_source=chatgpt.com "Pantheon 1.0, a manually verified dataset of globally famous biographies"
[4]: https://www.nature.com/articles/s41597-022-01369-4?utm_source=chatgpt.com "A cross-verified database of notable people, 3500BC-2018AD"
[5]: https://www.presidency.ucsb.edu/?utm_source=chatgpt.com "The American Presidency Project"
[6]: https://data.millercenter.org/?utm_source=chatgpt.com "data.millercenter.org"
[7]: https://www.govinfo.gov/app/collection/CPD/?utm_source=chatgpt.com "Compilation of Presidential Documents - GovInfo"
[8]: https://www.ungdc.bham.ac.uk/?utm_source=chatgpt.com "United Nations General Debate Corpus"
[9]: https://digitallibrary.un.org/record/4067189?utm_source=chatgpt.com "United Nations General Assembly general debate speeches /"
[10]: https://github.com/jradius/un-general-debates?utm_source=chatgpt.com "jradius/un-general-debates - GitHub"
[11]: https://partyfacts.herokuapp.com/data/parlspeech/?utm_source=chatgpt.com "PF · Datasets · parlspeech - herokuapp.com"
[12]: https://www.clarin.eu/resource-families/parliamentary-corpora?utm_source=chatgpt.com "Parliamentary Corpora | CLARIN ERIC - Common Language Resources and ..."
[13]: https://parllawspeech.org/data/?utm_source=chatgpt.com "ParlLawSpeech: The Data"
[14]: https://www.tensorflow.org/datasets/catalog/tedlium?utm_source=chatgpt.com "tedlium | TensorFlow Datasets"
[15]: https://www.kaggle.com/datasets/thedatabeast/ted-talk-transcripts-2006-2021?utm_source=chatgpt.com "TED Talk Transcripts (2006 - 2021) - Kaggle"
[16]: https://arxiv.org/abs/1906.03940?utm_source=chatgpt.com "Predicting TED Talk Ratings from Language and Prosody"
[17]: https://www.nobelprize.org/prizes/lists/video-lectures-and-acceptance-speeches-from-nobel-peace-prize-laureates/?utm_source=chatgpt.com "Video of Nobel Peace Prize lectures and acceptance speeches"
[18]: https://openalex.org/?utm_source=chatgpt.com "OpenAlex: The open catalog to the global research system | OpenAlex"
[19]: https://github.com/dataGHIA/SOPHIAS?utm_source=chatgpt.com "GitHub - dataGHIA/SOPHIAS"
[20]: https://github.com/dondongwon/LPMDataset?utm_source=chatgpt.com "GitHub - dondongwon/LPMDataset"
