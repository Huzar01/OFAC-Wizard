# OFAC Wizard
Searches OFAC database for sanction entities 


# How it works
This document explains the design, functionality, and structure of the OFAC Sanctions Search API. The API is implemented in a Python script (`main.py`) using Flask. It downloads the OFAC SDN XML data, allows you to search for sanctions entries by name, and provides two search endpoints (concise and full). A separate endpoint is provided to force a re-download of the database. An OpenAPI 3.1 schema is also provided to describe the API for integration with other tools.

---

## 1. Overview

The API performs the following functions:

- **Data Download:**  
  Downloads the latest OFAC SDN XML file from the official URL (<https://www.treasury.gov/ofac/downloads/sdn.xml>). This is done once at startup and can be reloaded via a dedicated endpoint.

- **Search Functionality:**  
  Allows the user (or client application) to search for sanctions entries by a given name. The search works by:
  - Collecting the official name (constructed from `<firstName>` and `<lastName>`) and any alternate names (from `<akaList>`).
  - Normalizing the text (removing punctuation and lowercasing).
  - Using a whole-word regular expression to check if the search term appears in any of the normalized variants.

- **Output:**  
  Two endpoints provide different levels of detail:
  - `/search_concise`: Returns only the matching names (a concise list).
  - `/search_full`: Returns detailed information for each match (Name, Address, Type, Program(s), List, and Score).

- **Database Reload:**  
  A POST endpoint `/reload` allows a client to clear the current in-memory database and download the latest version from the OFAC website.

---

## 2.  main.py

### 2.1. Module Imports and Global Variables

- **Imports:**  
  The script imports modules for regular expressions (`re`), string manipulation (`string`), HTTP requests (`requests`), XML parsing (`xml.etree.ElementTree`), and Flask’s web API functionality.
  
- **Global Variables:**  
  - `OFAC_URL` is set to the URL of the OFAC SDN XML file.
  - `ofac_xml_data` holds the downloaded XML data. It is initially `None` and is set when the script starts (or reloaded via the `/reload` endpoint).

### 2.2. Data Download

- **`fetch_ofac_data(url)` Function:**  
  This function downloads the XML data from the provided URL using the `requests` library. It returns the raw XML content if the HTTP request is successful (status code 200). In case of errors, it prints an error message and returns `None`.

### 2.3. Text Normalization

- **`normalize_name(text)` Function:**  
  This function normalizes any given text by:
  - Replacing all punctuation (commas, periods, hyphens, etc.) with spaces.
  - Converting the text to lower case.
  - Collapsing multiple spaces into one.
  
  This step ensures that variations in punctuation or capitalization do not affect the search.

### 2.4. Name Extraction and Variants

- **`get_official_name(entry, ns)` Function:**  
  This extracts the official name from an XML entry by combining the `<firstName>` and `<lastName>` elements. If the `<firstName>` element is missing, it uses only the `<lastName>`.

- **`collect_name_variants(entry, ns)` Function:**  
  In addition to the official name, many entries include alternate names in the `<akaList>` element. This function collects all these variants so that searches can match any version of a name.

### 2.5. Extracting Additional Details

- **`extract_address(entry, ns)` Function:**  
  This function navigates through the `<addressList>` element. It looks for common address tags (like `address1`, `address2`, `city`, `stateOrProvince`, `postalCode`, and `country`) and concatenates them together for each address. If more than one address exists, they are separated by `" | "`.

- **`extract_programs(entry, ns)` Function:**  
  This function gathers all `<program>` elements under `<programList>` and joins them with a semicolon (`; `) separator.

- **`extract_type(entry, ns)` Function:**  
  This extracts the sanction type (e.g., "Individual", "Entity", "Vessel") from the `<sdnType>` element.

### 2.6. Searching the XML Data

- **`search_sdn(xml_data, name_search)` Function:**  
  This is the core function that:
  1. Parses the XML data.
  2. Determines the XML namespace (if any).
  3. Iterates over each `<sdnEntry>` element.
  4. Collects all name variants for the entry and normalizes them.
  5. Uses a regex (with word boundaries) to check if the normalized search term appears as a whole word in any of the name variants.
  6. If a match is found, the function extracts:
     - **Name:** The official name.
     - **Address:** The concatenated address string.
     - **Type:** The sanction type.
     - **Program(s):** The programs associated with the entry.
     - **List:** Hardcoded to `"SDN"`.
     - **Score:** Hardcoded to `"100"`.
  7. Returns a list of dictionaries (one per matching entry).

### 2.7. API Endpoints

- **`/search_concise` (GET):**  
  Returns only the official names matching the search term.

- **`/search_full` (GET):**  
  Returns detailed information for each match.

- **`/reload` (POST):**  
  Forces a re-download of the OFAC XML data.

### 2.8. Application Startup

The script downloads the OFAC XML data once and then starts the Flask application on port 5000.

---

## 3. API Schema (OpenAPI 3.1)

The OpenAPI schema describes the API endpoints, parameters, and expected responses.

### 3.1. Endpoints

- **GET `/search_concise`**: Returns matching names.
- **GET `/search_full`**: Returns full entry details.
- **POST `/reload`**: Reloads the OFAC database.

---

## 4. How to Use the API

1. Run `main.py` to start the API.
2. Use `/search_concise?name=term` for concise search results.
3. Use `/search_full?name=term` for full details.
4. Use `/reload` to refresh the data.

---

## 5. Conclusion

This document explains the API code and OpenAPI schema, detailing its functionality and integration points.
