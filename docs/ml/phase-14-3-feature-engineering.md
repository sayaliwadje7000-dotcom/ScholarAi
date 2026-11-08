# Phase 14.3 — Feature Engineering and Feature Pipeline

## Objective

Build a reproducible feature-engineering architecture for
the ScholarAI recommendation model.

## Existing Architecture Reused

- StudyResource
- UserPreferences
- UserResourceInteraction
- ResourceEmbedding
- ContentFeatureExtractor
- ContentFeatureNormalizer

No database schema changes are introduced.

## Feature Groups

### User Features

- Preferred language
- Education level
- Preferred subjects
- Learning goals

### Resource Features

- Resource type
- Subject
- Language
- Difficulty
- Provider
- Categories

### Quality Features

- Quality score
- Estimated duration
- Resource age

### Interaction Features

- Historical views
- Historical clicks
- Historical saves
- Historical completions
- Historical ratings
- Historical average rating

### Content Features

- Title
- Description
- Topics
- Keywords
- Learning objectives
- Prerequisites

### Semantic Features

- Existing resource embeddings

## Transformation Architecture

Categorical:
- SimpleImputer
- OneHotEncoder

Numerical:
- SimpleImputer
- StandardScaler

Text:
- TF-IDF
- Unigrams and bigrams
- Sublinear term frequency

Composition:
- Scikit-learn ColumnTransformer

## Leakage Prevention

1. Interactions after prediction time are excluded.
2. Interactions with the target resource are excluded from
   historical user activity features.
3. Interactions belonging to other users are excluded.
4. User IDs and resource IDs are grouping keys only.
5. Direct user identifiers are not model features.

## Database Changes

None.

## Main Implementation Files

- features/feature_schema.py
- features/feature_extractor.py
- features/feature_transformer.py
- features/feature_pipeline.py

## Test Files

- test_feature_schema.py
- test_feature_extractor.py
- test_feature_transformer.py
- test_feature_pipeline.py

## Next Phase

Phase 14.4 — Baseline Machine-Learning Model.