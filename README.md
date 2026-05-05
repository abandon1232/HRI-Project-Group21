# Weekly Mental State Check-in: Empathetic Social Robot Interactions

This is the project repository for Human-Robot Interaction (1MD043 VT2026) by **Group 21**.
Team Members: Yihang Feng, Ruiji Huang, Weixun Ma, Chu Wang

## Introduction
This project aims to design and evaluate a Social Robot intervention to support university students' mental health during the challenging transition into adulthood. Using the Furhat robotic platform, we developed a "Weekly Mental State Check-in" application. The robot acts as an empathetic interviewer, conducting 3-minute sessions focused on students' feelings, activities, and social connections.

## Experimental Design
To test whether emotional expressiveness significantly enhances perceived empathy, we implemented two distinct interaction conditions. To prevent the confounding "Uncanny Valley" effect caused by modal mismatch, both conditions share an **identical, objectively phrased, and non-directive verbal script**. The independent variable is strictly isolated to the non-verbal channel.

- **Condition 1 (Empathetic):** High expressivity utilizing dynamic Face Textures, increased nodding frequency (e.g., nodding before asking questions), context-aware empathetic gestures (e.g., smiling for positive responses, frowning for negative), and an expressive neural voice model (Amazon Polly Joanna-Neural) to deliver in-situ physiological regulation and supportive feedback.
- **Condition 2 (Neutral):** A baseline version employing Furhat's default idle behavior, static facial expressions, a standard monotonic voice (Salli), and an absence of non-verbal supportive gestures, ensuring no empathetic valence is projected.

## Core Features
- **State-Machine Architecture:** Robust dialogue flow using the Furhat Python Realtime API.
- **Sentiment Analysis:** Keyword-based user response analysis dynamically triggers empathetic micro-expressions and gestures.
- **Ethical Safety Protocol:** A strict closed-loop safety mechanism inspired by clinical AI guidelines. If high-risk keywords (e.g., suicidal ideation or severe self-harm tendencies) are detected, the system instantly halts the interview and triggers an emergency intervention response providing the Uppsala University Student Health Service hotline.
- **Swedish Student Localization:** The dialogue script is culturally adapted to Swedish student life and mental health needs (e.g., mentions of Uppsala, winter days, fika).

## Usage
Ensure you have the Furhat SDK running locally on your machine, then execute one of the entry points:

```bash
# To run the Empathetic condition:
python HRI/condition1_empathetic.py

# To run the Neutral condition:
python HRI/condition2_neutral.py
```

Interaction transcripts and system events are automatically saved in the `logs/` directory.
