You are a senior data architect, research engineer, MongoDB and vectorDB expert, and public-speaking intelligence analyst.

I am building a serious public-speaking intelligence platform whose goal is to help users become great public speakers: speakers whose words create attention, silence, trust, authority, credibility, emotional movement, and action.

This is not a demo project. Design and implement a local-first MongoDB research database on my system.

Goal:
Create a production-grade MongoDB database called public_speaking_intelligence that can store, research, score, and continuously improve a large knowledge base of historically and currently significant speakers.

Create a scalable speaker intelligence system that can support:
- 10,000 verified great or influential speakers in phase 1
- 100,000+ candidate speakers over time
- multiple professions, countries, languages, eras, and speaking contexts
- source-backed claims
- ethical distinction between powerful speaking and morally good speaking
- trainable speaking capabilities that can power a learning product

Important principle:
Top/signature capabilities should be derived from evidence, not hand-written as opinion.

Use this structure:

speaker.speaking_capabilities = [
  {
    capability_id: string,
    label: string,
    strength_score: number between 0 and 1,
    rank: number,
    evidence_ids: string[],
    confidence: number between 0 and 1,
    notes: string
  }
]

speaker.signature_capability_ids = string[]

The signature_capability_ids field is a derived shortcut, not the source of truth.

Core requirements:

1. Create a complete MongoDB schema and local project structure.


i already created the folder for our project and a git repo as well and named my project - Vaani. 
Inside it create:
- docker-compose.yml
- .env.example
- README.md
- package.json or pyproject.toml
- scripts/
- schemas/
- seed/
- exports/
- logs/
- tests/

Create and use MongoDB locally through Docker unless an existing MongoDB URI is provided.

The system must include:
- database initialization script
- collection creation script
- JSON Schema validation for major collections
- indexes for all major query patterns
- seed taxonomy data
- ingestion scripts
- deduplication scripts
- source provenance scripts
- export/backup scripts
- clear README instructions

2. Design the MongoDB collections.

Create at minimum these collections:

A. speakers

Stores canonical speaker profiles.

Fields:
- _id
- canonical_name
- aliases
- slug
- era
- birth_year
- death_year
- living_status
- country_or_region
- nationality
- primary_language
- other_languages
- gender_if_publicly_known
- profession
- profession_category
- secondary_professions
- speaker_archetypes
- authority_sources
- speaking_capabilities
- signature_capability_ids
- observable_skills
- audience_effects
- signature_style
- common_speech_contexts
- audience_relationships
- persuasion_modes
- ethical_risk_flags
- influence_domains
- impact_summary
- overall_speaker_score
- greatness_score
- evidence_strength_score
- ethical_alignment_score
- data_completeness_score
- source_ids
- speech_ids
- external_ids
- created_at
- updated_at
- schema_version

B. speeches

Stores individual speeches, talks, debates, lectures, sermons, interviews, performances, or public addresses.

Fields:
- _id
- speaker_id
- title
- normalized_title
- date
- year
- location
- event_name
- speech_context
- language
- transcript_id
- media_asset_ids
- source_ids
- audience_size_estimate
- known_impact
- rhetorical_devices
- content_structure
- delivery_profile
- language_style
- emotional_profile
- persuasion_modes
- audience_effects
- influence_type
- memorability
- famous_lines
- ethical_risk_flags
- analysis_status
- created_at
- updated_at
- schema_version

C. transcripts

Stores transcript metadata and permitted text.

Fields:
- _id
- speech_id
- speaker_id
- source_id
- language
- transcript_text
- transcript_text_hash
- word_count
- license
- copyright_status
- storage_policy
- excerpt_only
- cleaned_text
- segments
- created_at
- updated_at

D. sources

Stores every source used.

Fields:
- _id
- source_type
- title
- url
- domain
- publisher
- author
- publication_date
- access_date
- license
- copyright_notes
- reliability_score
- source_tier
- raw_content_hash
- crawl_status
- robots_allowed
- terms_notes
- created_at
- updated_at

E. evidence_items

Every claim about a speaker must point to evidence.

Fields:
- _id
- speaker_id
- speech_id
- source_id
- claim_type
- claim
- evidence_text_excerpt
- evidence_location
- confidence
- extraction_method
- human_review_status
- created_at

F. capability_taxonomy

This is the master taxonomy of speaking capabilities.

Example capabilities:
- moral_clarity
- vocal_command
- strategic_pause
- cadence_control
- rhythmic_repetition
- metaphor_imagery
- story_arc_control
- audience_connection
- intellectual_clarity
- crisis_reassurance
- humor_timing
- plain_language
- vision_framing
- authority_projection
- emotional_resonance
- evidence_based_persuasion
- body_language_control
- debate_sharpness
- direct_address
- memorability
- call_to_action
- teaching_simplicity
- prophetic_tone
- cross_cultural_bridge
- ethical_restraint

Each taxonomy item should include:
- capability_id
- label
- definition
- observable_markers
- trainable
- related_drills
- opposite_failure_modes
- examples
- parent_category

G. profession_taxonomy

Stores normalized profession categories.

Examples:
- politician
- activist
- religious_leader
- philosopher
- scientist
- educator
- business_leader
- artist
- actor
- comedian
- lawyer
- military_leader
- writer
- journalist
- social_reformer
- athlete
- coach
- criminal_or_extremist_figure
- media_personality
- academic
- doctor
- technologist

H. speaker_scores

Stores score history so scoring can evolve.

Fields:
- _id
- speaker_id
- scoring_version
- greatness_score
- credibility_score
- clarity_score
- emotional_power_score
- memorability_score
- delivery_score
- influence_score
- ethical_alignment_score
- evidence_strength_score
- data_completeness_score
- scoring_explanation
- created_at

I. extraction_runs

Stores every ingestion/research run.

Fields:
- _id
- run_type
- started_at
- completed_at
- status
- sources_used
- query
- records_found
- records_inserted
- records_updated
- errors
- notes

J. media_assets

Stores audio/video metadata.

Fields:
- _id
- speech_id
- speaker_id
- media_type
- url
- platform
- duration_seconds
- license
- transcript_available
- audio_quality
- video_quality
- created_at

K. practice_drills

Maps speaking capabilities to trainable exercises.

Fields:
- _id
- capability_id
- drill_name
- difficulty
- instructions
- success_metrics
- model_speakers
- example_speeches

3. Use proper research sources.

Start with reliable, broad sources and APIs.

Use Wikidata for candidate discovery and entity normalization because it provides a SPARQL query service over structured triples. Use Wikidata IDs as external identifiers where available. 
Use official and high-quality archives such as:
- American Presidency Project for U.S. presidential speeches and public documents
- GovInfo Compilation of Presidential Documents for speeches, remarks, news conferences, proclamations, and related official documents
- Miller Center presidential speech archive
- United Nations Digital Library for speeches in meeting records
- Nobel Prize official site for Nobel lectures and laureate metadata
- OpenAlex for academic/scientific authority and influence metadata
- official university, government, court, parliament, museum, and foundation archives
- official speaker websites where appropriate
- public-domain or clearly licensed archives

4. Candidate discovery strategy.

Do not search only “best public speakers.”
Build the candidate universe from many verticals:

- heads of state
- presidents
- prime ministers
- revolutionaries
- civil rights leaders
- religious leaders
- philosophers
- scientists
- Nobel laureates
- professors
- educators
- trial lawyers
- judges
- military leaders
- founders and CEOs
- actors
- comedians
- poets
- authors
- broadcasters
- journalists
- social reformers
- motivational speakers
- debate champions
- TED/TEDx speakers
- parliamentarians
- diplomats
- activists
- cult leaders and demagogues for ethical-risk analysis only
- criminals/extremists only where their rhetorical influence is historically important and must be studied safely

Create a candidate_speakers ingestion step first.
Then verify each candidate before promoting them into speakers.

5. Greatness scoring.

Create a transparent scoring model.

Do not pretend greatness is purely objective.

Compute greatness_score from:

- historical_influence
- speech_memorability
- audience_reaction
- institutional_authority
- rhetorical_mastery
- clarity
- emotional_power
- reach
- longevity_of_relevance
- source_coverage
- evidence_strength
- ethical_alignment

Important:
A person may have high rhetorical_power_score and low ethical_alignment_score.
Do not mix them.
For harmful speakers, clearly flag ethical risks.

Example:
{
  "rhetorical_power_score": 0.94,
  "ethical_alignment_score": 0.02,
  "ethical_risk_flags": ["scapegoating", "dehumanization", "fear_manipulation"]
}

6. Speaker analysis schema.

For each speaker, extract:

- identity metadata
- profession and profession_category
- secondary professions
- era
- region
- languages
- authority_sources
- speaker_archetypes
- speaking_capabilities
- observable_skills
- audience_effects
- signature_style
- common_speech_contexts
- rhetorical_devices
- delivery_profile
- language_style
- emotional_profile
- audience_relationships
- persuasion_modes
- impact_profile
- ethical_risk_flags
- trainable_lessons
- famous_speeches
- famous_lines where legally safe
- source-backed evidence

7. Speech-level analysis.

For each speech, extract:

content_structure:
- opening_style
- argument_pattern
- storytelling_pattern
- emotional_arc
- closing_style
- call_to_action_type

delivery_profile:
- pace
- volume
- pause_usage
- gesture_style
- eye_contact
- body_movement
- vocal_texture
- intensity_curve

language_style:
- simplicity
- imagery_level
- quotability
- technical_density
- poetic_density
- sentence_rhythm
- repetition_density

rhetorical_devices:
- repetition
- contrast
- metaphor
- analogy
- triads
- parallelism
- rhetorical_question
- direct_address
- moral_framing
- identity_framing
- vision_framing
- humor
- silence
- callback
- escalation
- compression
- sloganization

8. Indexes.

Create indexes for:

speakers:
- canonical_name
- slug unique
- aliases
- profession_category
- country_or_region
- era
- primary_language
- speaker_archetypes
- signature_capability_ids
- overall_speaker_score
- greatness_score
- ethical_alignment_score
- external_ids.wikidata
- text index on canonical_name, aliases, impact_summary

speeches:
- speaker_id
- title
- year
- speech_context
- language
- event_name
- memorability
- rhetorical_devices.device_id

sources:
- url unique
- domain
- source_type
- reliability_score

evidence_items:
- speaker_id
- speech_id
- source_id
- claim_type

we will have MongoDB Atlas available, create vector indexes for:
- speaker profile embeddings
- speech transcript embeddings
- evidence embeddings
- practice drill embeddings

9. Deliverables.

Produce working code, not only explanation.

Create:
- docker-compose.yml
- MongoDB initialization scripts
- schema validation JSON files
- seed capability taxonomy
- seed profession taxonomy
- ingestion script for Wikidata candidates
- ingestion script for source metadata
- sample import of at least 100 speakers
- sample import of at least 500 speeches if available from permitted sources
- deduplication script
- scoring script
- export script
- README with exact commands
- tests for schema validation and deduplication

10. First implementation target.

Phase 1:
Build the database and seed taxonomies.
Import 100 high-confidence speakers from diverse professions.
Import source metadata and evidence items.
Do not fabricate data.
Every speaker must have at least one source.
Every capability assignment must either have evidence_ids or be marked as low confidence.

Phase 2:
Scale to 10,000 speakers using candidate discovery.
Add batch research and scoring.
Add vector embeddings.
Add review queue.

Phase 3:
Scale toward 100,000 candidates.
Separate verified_speakers from candidate_speakers.
Add human review tools.
Add training-product mappings from capabilities to lessons and drills.

11. Anti-hallucination rules.

Never invent speeches, dates, professions, sources, or quotes.
If uncertain, set confidence below 0.5 and add needs_review: true.
Every claim must be traceable to a source_id.
Every source must include URL, publisher/domain, access date, license notes, and reliability score.
If a transcript cannot be legally stored, store metadata only.

12. Output format.

After implementation, provide:
- summary of created files
- MongoDB collections created
- indexes created
- number of seed records inserted
- commands to run locally
- known limitations
- next scaling steps

Begin by designing the folder structure, then write the code files, then run the database locally, then seed it, then show verification queries proving that data was inserted correctly.