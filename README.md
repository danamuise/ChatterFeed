# ChatterFeed
##What would online discourse look like if language became gesture?

ChatterFeed is a temporary, non-commercial artwork created by an independent artist. It uses publicly available Reddit posts and comments as live input for a physical, kinetic art installation. The project is not intended to generate revenue, build a commercial product, profile individual users, or create a permanent archive of Reddit content.

## Purpose

The goal of ChatterFeed is to translate the emotional character of online human communication into physical marks on paper.

Software analyzes incoming messages for broad forms of expression such as kindness, affection, encouragement, hostility, hate speech, or aggression. These classifications are translated into different movements by a robotic drawing arm. Supportive or affectionate language may produce gentle, controlled, or colorful marks, while hostile or aggressive language may result in more forceful and chaotic gestures.

The resulting drawing gradually becomes a physical interpretation of the range of human expression encountered during the installation.

The intended message of the artwork is that language has an emotional and physical presence even when it is communicated through a digital interface. ChatterFeed makes those otherwise intangible interactions visible by allowing words and tone to directly influence the creation of a changing physical artwork.

## Reddit Data and Privacy

**No Reddit data will be collected, archived, or permanently stored by the project.**

Reddit content will be accessed only temporarily while the installation is running and used solely as live input to the artwork. The system will not save usernames, user profiles, account information, post histories, or other identifying information.

Any Reddit text displayed as part of the installation will be presented anonymously. **Usernames and other personal or identifying information will not be shown.**

Messages will be processed before display. Obscenities, slurs, hate speech, and other offensive language will be redacted so that this language is not reproduced directly to viewers.

The project does not create a searchable database, dataset, archive, or secondary collection of Reddit content. Messages are processed transiently, classified for their broad emotional or linguistic characteristics, and then discarded after they have served as input to the installation.

## Observation Scope

For the purposes of the artwork, we would like to observe communication within a defined group of highly active Reddit communities. The intention is to sample a broad range of everyday public conversation while keeping the scope of the project limited and clearly identified.

The subreddits we would like to observe are:

1. **r/AskReddit** — ~4.93 million posts/comments
2. **r/redditgames** — ~2.58 million
3. **r/meowi** — ~2.21 million
4. **r/tierlistfills** — ~2.06 million
5. **r/bunnytrials** — ~1.71 million
6. **r/NoStupidQuestions** — ~1.41 million
7. **r/nfl** — ~1.40 million
8. **r/askanything** — ~1.23 million
9. **r/classicwow** — ~1.14 million
10. **r/mildlyinfuriating** — ~1.14 million

## Technical Overview

The installation consists of a Raspberry Pi-based application that accesses a limited stream of publicly available Reddit content through Reddit's authorized API.

The text is processed locally and assigned broad contextual or emotional categories. Those classifications are then converted into movement commands for a programmable robotic arm, which creates marks on paper using physical drawing materials.

ChatterFeed is an experimental artwork intended for temporary exhibition and artistic research. Reddit data would be used only to enable the live behavior of the installation and would not be used for commercial exploitation, advertising, user surveillance, profiling, dataset creation, resale, or redistribution.
