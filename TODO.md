- Add resizable split pane between search results and PDF viewer using Split.js library
- Redesign search box. Have a drop-down menu containing the favorite star, the favorites button, and the index button.
- Allow direct opening a specific volume in pdf viewer without text search. Current attempt with special character @GA_234 isn't guaranteed to work. This could be a separate item on the drop-down menu introduced above.
- For hits that refer to a lecture cycle volume, extend the hover text currently displaying the book title in the search result panel with the time and place of the cycle.
  - Publication date of the volume is not important. Maintain the link to anthrowiki.at.
  - For dates, use DD.MM.YYYY format, or single digits to avoid leading zeroes (for example "Berlin, 15.5 - 3.6.1911"). 
  - extract this information given the first pages as last step of indexing and store result in JSON file in index folder for later retrieval. Provide a separate script in scripts to refresh this information in case changes are made in the format.

