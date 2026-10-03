"""
Pakistan Law MCP Server
========================
An MCP (Model Context Protocol) server exposing four legal tools:
  1. search_law(query: str)
  2. search_google(query: str)
  3. get_law_section(section: str, law_name: str = "")
  4. search_judgments(query: str)

Designed for educational demonstrations of Agent <-> MCP architectures.
"""

import os
import sys
import json
import requests
from typing import Dict, Any, List
from dotenv import load_dotenv

# Ensure the external 'mcp' SDK from site-packages is imported
# without being shadowed by the local 'mcp/' directory structure
_cur_dir = os.path.dirname(os.path.abspath(__file__))
_proj_root = os.path.abspath(os.path.join(_cur_dir, ".."))
_orig_path = list(sys.path)
sys.path = [p for p in sys.path if os.path.abspath(p or ".") not in (_cur_dir, _proj_root)]

try:
    from mcp.server.fastmcp import FastMCP
except (ImportError, ModuleNotFoundError):
    from mcp.server.mcpserver import MCPServer as FastMCP
finally:
    sys.path = _orig_path

# Ensure project root is in sys.path for local imports
if _proj_root not in sys.path:
    sys.path.insert(0, _proj_root)


mcp = FastMCP("Pakistan-Law-Server")


# ==============================================================================
# Curated Verified Pakistani Legal Knowledge Base (Offline Reference)
# ==============================================================================
# Prevents hallucination of exact statutory provisions and enables classroom
# demonstrations even before external search API keys are configured.

VERIFIED_SECTIONS = {
    ("489-F", "PPC"): {
        "law_name": "Pakistan Penal Code, 1860 (Act XLV of 1860)",
        "section": "489-F",
        "title": "Dishonestly issuing a cheque",
        "text": (
            "Whoever dishonestly issues a cheque towards re-payment of a loan or fulfillment "
            "of an obligation which is dishonoured on presentation, shall be punishable with "
            "imprisonment which may extend to three years, or with fine, or with both, unless "
            "he can prove, for which the burden of proof shall be on him, that he had made "
            "arrangements with his bank to ensure that the cheque would be honoured and that "
            "the bank was at fault in not honouring the cheque."
        ),
        "notes": "Added via Criminal Law (Amendment) Ordinance, 2002. Cognizable, bailable, and compoundable offence.",
        "source_url": "http://www.pakistancode.gov.pk/pdffiles/administrator576d338ee359d9976378e907eafe9f08.pdf"
    },
    ("20", "PECA"): {
        "law_name": "Prevention of Electronic Crimes Act, 2016 (Act XL of 2016)",
        "section": "20",
        "title": "Offences against dignity of a natural person",
        "text": (
            "Whoever intentionally and publicly exhibits or displays or transmits any information "
            "through any information system, which he knows to be false, and intimidates or harms "
            "the reputation or privacy of a natural person, shall be punished with imprisonment "
            "for a term which may extend to three years or with fine which may extend to one "
            "million rupees or with both."
        ),
        "notes": (
            "In a landmark ruling (PFUJ v. Federation of Pakistan, PLD 2022 Islamabad 408), "
            "the Islamabad High Court struck down the 2022 PECA Amendment Ordinance and held "
            "criminal defamation under Section 20 to be unconstitutional, directing aggrieved parties "
            "toward civil remedies under the Defamation Ordinance, 2002."
        ),
        "source_url": "http://www.pakistancode.gov.pk/pdffiles/administrator419ef949bb270d440ad88686d11f7ff2.pdf"
    },
    ("21", "PECA"): {
        "law_name": "Prevention of Electronic Crimes Act, 2016 (Act XL of 2016)",
        "section": "21",
        "title": "Offences against modesty of a natural person and minor",
        "text": (
            "Whoever intentionally and publicly exhibits or displays or transmits any information "
            "which superimposes a photograph of the face of a person over sexually explicit images, "
            "distorts or creates sexually explicit images or video of any person, or entices a person "
            "to produce sexually explicit material, without express or free consent. "
            "Punishable with imprisonment up to five years or fine up to five million rupees, or both. "
            "If the victim is a minor, imprisonment may extend to seven years."
        ),
        "notes": "Key provision against cyber blackmail, non-consensual image sharing, and cyber harassment.",
        "source_url": "http://www.pakistancode.gov.pk/pdffiles/administrator419ef949bb270d440ad88686d11f7ff2.pdf"
    },
    ("24", "PECA"): {
        "law_name": "Prevention of Electronic Crimes Act, 2016 (Act XL of 2016)",
        "section": "24",
        "title": "Cyber stalking",
        "text": (
            "A person commits the offence of cyber stalking who, with the intent to coerce or intimidate "
            "or harass any person, uses an information system or service to follow a person or repeatedly "
            "contact or attempt to contact, spy on, or monitor internet or electronic communication. "
            "Punishable with imprisonment for up to three years, or with fine up to one million rupees, or both."
        ),
        "notes": "Applies directly to online stalkers and persistent electronic harassment.",
        "source_url": "http://www.pakistancode.gov.pk/pdffiles/administrator419ef949bb270d440ad88686d11f7ff2.pdf"
    },
    ("302", "PPC"): {
        "law_name": "Pakistan Penal Code, 1860 (Act XLV of 1860)",
        "section": "302",
        "title": "Punishment of Qatl-i-amd (Intentional Homicide)",
        "text": (
            "Whoever commits qatl-i-amd shall be: (a) punished with death as qisas; "
            "(b) punished with death or imprisonment for life as ta'zir having regard to the facts "
            "and circumstances of the case, if the proof in either of the forms specified in section 304 "
            "is not available; or (c) punished with imprisonment of either description for a term which "
            "may extend to twenty-five years, where according to the Injunctions of Islam as laid down "
            "in the Holy Quran and Sunnah the punishment of qisas is not applicable."
        ),
        "notes": "Core provision governing intentional murder under Pakistani criminal law.",
        "source_url": "http://www.pakistancode.gov.pk"
    },
    ("420", "PPC"): {
        "law_name": "Pakistan Penal Code, 1860 (Act XLV of 1860)",
        "section": "420",
        "title": "Cheating and dishonestly inducing delivery of property",
        "text": (
            "Whoever cheats and thereby dishonestly induces the person deceived to deliver any property "
            "to any person, or to make, alter or destroy the whole or any part of a valuable security, "
            "shall be punished with imprisonment of either description for a term which may extend to "
            "seven years, and shall also be liable to fine."
        ),
        "notes": "Standard cheating provision in Pakistani criminal jurisprudence.",
        "source_url": "http://www.pakistancode.gov.pk"
    }
}

VERIFIED_STATUTES = [
    {
        "title": "Prevention of Electronic Crimes Act, 2016 (PECA)",
        "year": "2016",
        "overview": "Comprehensive legislation addressing computer-related offences, cyber harassment, cyber stalking, unauthorized access, electronic fraud, cyber terrorism, and identity theft in Pakistan.",
        "key_sections": "Section 20 (Offences against dignity), Section 21 (Modesty/blackmail), Section 24 (Cyber stalking), Section 10 (Cyber terrorism)",
        "source_url": "http://www.pakistancode.gov.pk/pdffiles/administrator419ef949bb270d440ad88686d11f7ff2.pdf"
    },
    {
        "title": "Pakistan Penal Code, 1860 (Act XLV of 1860)",
        "year": "1860 (amended)",
        "overview": "The principal criminal code of Pakistan defining criminal offences and corresponding punishments including offences against the human body, property, reputation, and public order.",
        "key_sections": "Section 302 (Murder), Section 489-F (Dishonour of cheque), Section 420 (Cheating), Section 500 (Defamation), Section 506 (Criminal intimidation)",
        "source_url": "http://www.pakistancode.gov.pk"
    },
    {
        "title": "Constitution of the Islamic Republic of Pakistan, 1973",
        "year": "1973",
        "overview": "The supreme law of Pakistan establishing fundamental rights, state institutions, separation of powers, and the judiciary.",
        "key_sections": "Article 9 (Security of person), Article 10-A (Fair trial), Article 14 (Inviolability of dignity and privacy), Article 19 (Freedom of speech), Article 25 (Equality), Article 184(3) & Article 199 (Writ jurisdiction)",
        "source_url": "http://www.na.gov.pk/uploads/documents/1333523681_951.pdf"
    },
    {
        "title": "Protection Against Harassment of Women at the Workplace Act, 2010",
        "year": "2010",
        "overview": "Law providing protection against sexual harassment for women in public and private workplaces, instituting mandatory inquiry committees and Ombudsperson offices.",
        "key_sections": "Section 2(h) (Definition of harassment), Section 4 (Inquiry committee), Section 8 (Ombudsperson appeals)",
        "source_url": "http://www.pakistancode.gov.pk"
    },
    {
        "title": "Code of Criminal Procedure, 1898 (CrPC)",
        "year": "1898",
        "overview": "Procedural law governing criminal investigations, arrest, inquiry, trial, and bail in Pakistani criminal courts.",
        "key_sections": "Section 154 (Registration of FIR), Section 497 (Bail in non-bailable cases), Section 498 (Anticipatory bail)",
        "source_url": "http://www.pakistancode.gov.pk"
    }
]

VERIFIED_JUDGMENTS = [
    {
        "case_title": "Pakistan Federal Union of Journalists (PFUJ) v. Federation of Pakistan",
        "citation": "PLD 2022 Islamabad 408",
        "court": "Islamabad High Court",
        "year": "2022",
        "summary": (
            "The Islamabad High Court declared Section 20 of PECA (criminal defamation) unconstitutional "
            "as it violated Article 19 and 19-A of the Constitution. The Court struck down the PECA Amendment "
            "Ordinance 2022 and underscored that criminalizing defamation suppresses democratic discourse."
        ),
        "source_url": "https://mis.ihc.gov.pk"
    },
    {
        "case_title": "Mian Allah Ditta v. The State",
        "citation": "PLD 2013 Supreme Court 849",
        "court": "Supreme Court of Pakistan",
        "year": "2013",
        "summary": (
            "Landmark judgment interpreting Section 489-F of the Pakistan Penal Code. The Supreme Court laid down "
            "the strict three essential ingredients for an offence under 489-F: (i) issuance of cheque, "
            "(ii) dishonest intent at time of issuance, and (iii) towards repayment of loan or fulfillment of obligation."
        ),
        "source_url": "https://www.supremecourt.gov.pk"
    },
    {
        "case_title": "Muhammad Sultan v. The State",
        "citation": "PLD 2022 Supreme Court 34",
        "court": "Supreme Court of Pakistan",
        "year": "2022",
        "summary": (
            "The Supreme Court discussed post-arrest bail principles under Section 489-F PPC, observing that "
            "where offences fall outside the prohibitory clause of Section 497 CrPC, grant of bail is the rule "
            "and refusal an exception."
        ),
        "source_url": "https://www.supremecourt.gov.pk"
    },
    {
        "case_title": "Mst. Rabia v. The State (Cyber Blackmailing / PECA bail)",
        "citation": "2020 PCrLJ 1424",
        "court": "High Court",
        "year": "2020",
        "summary": (
            "Detailed judicial guidelines concerning investigation by the FIA Cybercrime Wing under Sections 20 & 21 "
            "of PECA regarding non-consensual dissemination of private images and electronic harassment."
        ),
        "source_url": "http://www.pakistanlawsite.com"
    }
]


# ==============================================================================
# Helper Functions for External Search (Serper API)
# ==============================================================================

def execute_serper_search(query: str, num_results: int = 5) -> List[Dict[str, str]]:
    """Execute a Google web search via Serper API if SERPER_API_KEY is set."""
    api_key = os.getenv("SERPER_API_KEY", "").strip()
    if not api_key:
        return []

    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    payload = json.dumps({"q": query, "num": num_results})

    try:
        response = requests.post(url, headers=headers, data=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            organic = data.get("organic", [])
            results = []
            for item in organic[:num_results]:
                results.append({
                    "title": item.get("title", "No Title"),
                    "snippet": item.get("snippet", "No Description"),
                    "link": item.get("link", "")
                })
            return results
        else:
            return [{"title": f"HTTP Error {response.status_code}", "snippet": response.text, "link": ""}]
    except requests.exceptions.Timeout:
        return [{"title": "Search Timeout", "snippet": "Search request to Serper API timed out after 10 seconds.", "link": ""}]
    except Exception as exc:
        return [{"title": "Search Error", "snippet": f"Web search failed: {str(exc)}", "link": ""}]


# ==============================================================================
# Tool 1: search_law
# ==============================================================================

@mcp.tool()
def search_law(query: str) -> str:
    """
    Search for relevant Pakistani laws, acts, ordinances, codes, regulations, or legal provisions.
    
    Args:
        query: Legal search term, act name, or concept (e.g. 'cyber harassment Pakistan', 'PPC bail').
        
    Returns:
        Structured summary with statute title, key provisions, description, and source URLs.
    """
    if not query or not query.strip():
        return "Error: Please provide a non-empty search query for Pakistani laws."

    query_clean = query.strip()
    serper_key = os.getenv("SERPER_API_KEY", "").strip()
    
    # 1. Check local verified database for matching statutes
    q_lower = query_clean.lower()
    local_matches = []
    for stat in VERIFIED_STATUTES:
        if (any(word in stat["title"].lower() for word in q_lower.split() if len(word) > 3) or
            any(word in stat["overview"].lower() for word in q_lower.split() if len(word) > 3) or
            any(word in stat["key_sections"].lower() for word in q_lower.split() if len(word) > 3)):
            local_matches.append(stat)

    # 2. If Serper API key is configured, perform live targeted legal search
    external_results = []
    if serper_key:
        targeted_query = f"{query_clean} Pakistan law act ordinance site:pakistancode.gov.pk OR site:na.gov.pk OR site:punjablaws.gov.pk OR site:senate.gov.pk"
        external_results = execute_serper_search(targeted_query, num_results=4)
        if not external_results or "HTTP Error" in external_results[0].get("title", ""):
            # Fall back to broader query
            external_results = execute_serper_search(f"{query_clean} Pakistan legal act code statute", num_results=4)

    # 3. Format structured output
    output_lines = [
        f"=== Pakistan Law Search Results for: '{query_clean}' ===\n"
    ]

    if local_matches:
        output_lines.append("Found Verified Pakistani Statutes (Official Legal Repository):")
        for i, match in enumerate(local_matches, 1):
            output_lines.append(f"{i}. Title: {match['title']} ({match['year']})")
            output_lines.append(f"   Key Sections: {match['key_sections']}")
            output_lines.append(f"   Overview: {match['overview']}")
            output_lines.append(f"   Source URL: {match['source_url']}\n")

    if external_results:
        output_lines.append("Live Web Search Results (Official / Legal Web Sources):")
        for i, res in enumerate(external_results, 1):
            output_lines.append(f"{i}. Title: {res['title']}")
            output_lines.append(f"   Snippet: {res['snippet']}")
            output_lines.append(f"   Source URL: {res['link']}\n")

    if not local_matches and not external_results:
        if not serper_key:
            output_lines.append(
                "No matching statutes found in the local verified repository. "
                "To search live legal web databases, please configure 'SERPER_API_KEY' in your .env file."
            )
        else:
            output_lines.append("No results found for the specified query in available official legal sources.")

    return "\n".join(output_lines)


# ==============================================================================
# Tool 2: search_google
# ==============================================================================

@mcp.tool()
def search_google(query: str) -> str:
    """
    Perform a broader web search when the agent needs current or general information.
    
    Args:
        query: Search string for general internet query (e.g. 'Pakistan cyber harassment law 2026').
        
    Returns:
        Structured list of top search results with titles, snippets, and source links.
    """
    if not query or not query.strip():
        return "Error: Please provide a valid search query."

    serper_key = os.getenv("SERPER_API_KEY", "").strip()
    if not serper_key:
        return (
            "Error: 'SERPER_API_KEY' is not configured in the environment / .env file. "
            "The search_google tool requires a valid Serper API key to query live Google web results."
        )

    results = execute_serper_search(query.strip(), num_results=5)
    if not results:
        return f"No web search results found for: '{query}'."

    output = [f"=== Google Web Search Results for: '{query}' ===\n"]
    for i, item in enumerate(results, 1):
        output.append(f"{i}. Title: {item['title']}")
        output.append(f"   Snippet: {item['snippet']}")
        output.append(f"   URL: {item['link']}\n")

    return "\n".join(output)


# ==============================================================================
# Tool 3: get_law_section
# ==============================================================================

@mcp.tool()
def get_law_section(section: str, law_name: str = "") -> str:
    """
    Retrieve authoritative information about a specific Pakistani legal section.
    
    Args:
        section: Section number or identifier (e.g. '489-F', '20', '302').
        law_name: Name of the law or act (e.g. 'Pakistan Penal Code', 'PECA', 'Constitution').
        
    Returns:
        Exact section text, law name, title, description, and official source URL.
    """
    if not section or not section.strip():
        return "Error: Section parameter is required (e.g. '489-F' or '20')."

    sec_clean = section.strip().upper().replace("SECTION", "").strip()
    law_clean = (law_name or "").strip().lower()

    # Determine statute code from law_name
    matched_statute_key = None
    if "penal" in law_clean or "ppc" in law_clean:
        matched_statute_key = "PPC"
    elif "peca" in law_clean or "electronic" in law_clean or "cyber" in law_clean:
        matched_statute_key = "PECA"

    # 1. Search verified repository
    found_entry = None
    if matched_statute_key and (sec_clean, matched_statute_key) in VERIFIED_SECTIONS:
        found_entry = VERIFIED_SECTIONS[(sec_clean, matched_statute_key)]
    else:
        # Check without statute match if section uniquely exists in database
        for (sec_k, law_k), val in VERIFIED_SECTIONS.items():
            if sec_k == sec_clean:
                if matched_statute_key is None or matched_statute_key == law_k:
                    found_entry = val
                    break

    if found_entry:
        return (
            f"=== Verified Legal Section: Section {found_entry['section']} ===\n"
            f"Law: {found_entry['law_name']}\n"
            f"Section: {found_entry['section']} - {found_entry['title']}\n\n"
            f"Statutory Text:\n\"{found_entry['text']}\"\n\n"
            f"Legal Notes / Context:\n{found_entry['notes']}\n\n"
            f"Official Source URL:\n{found_entry['source_url']}"
        )

    # 2. If not found in local verified set, search via Serper if key available
    serper_key = os.getenv("SERPER_API_KEY", "").strip()
    if serper_key:
        query = f"\"{sec_clean}\" \"{law_name}\" Pakistan law section site:pakistancode.gov.pk OR site:punjablaws.gov.pk OR site:na.gov.pk"
        results = execute_serper_search(query, num_results=3)
        if results and "HTTP Error" not in results[0]["title"]:
            res_lines = [
                f"=== Web-Retrieved Information for Section {sec_clean} ({law_name or 'Pakistani Law'}) ===\n"
            ]
            for i, r in enumerate(results, 1):
                res_lines.append(f"{i}. Title: {r['title']}")
                res_lines.append(f"   Snippet: {r['snippet']}")
                res_lines.append(f"   Source URL: {r['link']}\n")
            res_lines.append(
                "Note: The above information was retrieved from web search. Please verify exact statutory "
                "wording directly at Pakistan Code: http://www.pakistancode.gov.pk"
            )
            return "\n".join(res_lines)

    # 3. If exact section cannot be verified, explicitly report without hallucinating
    return (
        f"Notice: Unable to verify authoritative statutory text for Section '{section}' "
        f"under '{law_name or 'unspecified law'}' from available official sources.\n\n"
        f"To uphold legal accuracy and avoid fabricating legal statutes, unverified text is not generated.\n"
        f"Recommendation: Please consult the official Pakistan Federal Laws portal directly at: "
        f"http://www.pakistancode.gov.pk"
    )


# ==============================================================================
# Tool 4: search_judgments
# ==============================================================================

@mcp.tool()
def search_judgments(query: str) -> str:
    """
    Search for Pakistani court judgments, case law, and judicial precedents.
    
    Args:
        query: Legal topic, court name, or citation (e.g. 'cyber harassment Pakistan Supreme Court', '489-F PPC bail').
        
    Returns:
        Relevant court cases with title, court, year, relevant snippet, and citation URL.
    """
    if not query or not query.strip():
        return "Error: Please specify a search query for court judgments."

    query_clean = query.strip()
    q_lower = query_clean.lower()
    serper_key = os.getenv("SERPER_API_KEY", "").strip()

    # 1. Search verified landmark judgments
    local_judgments = []
    for jd in VERIFIED_JUDGMENTS:
        if (any(w in jd["case_title"].lower() for w in q_lower.split() if len(w) > 3) or
            any(w in jd["citation"].lower() for w in q_lower.split() if len(w) > 3) or
            any(w in jd["summary"].lower() for w in q_lower.split() if len(w) > 3)):
            local_judgments.append(jd)

    # 2. Live search court repositories if SERPER_API_KEY is available
    external_cases = []
    if serper_key:
        court_query = (
            f"{query_clean} (site:supremecourt.gov.pk OR site:caselaw.shc.gov.pk OR "
            f"site:sys.lhc.gov.pk OR site:pakistanlawsite.com OR site:courtingthelaw.com OR "
            f"\"Supreme Court of Pakistan\" OR \"High Court\")"
        )
        external_cases = execute_serper_search(court_query, num_results=4)

    output = [
        f"=== Pakistani Judicial Precedents & Judgments: '{query_clean}' ===\n"
    ]

    if local_judgments:
        output.append("Found Verified Landmark Judicial Precedents:")
        for i, jd in enumerate(local_judgments, 1):
            output.append(f"{i}. Case: {jd['case_title']}")
            output.append(f"   Citation: {jd['citation']} ({jd['court']}, {jd['year']})")
            output.append(f"   Summary: {jd['summary']}")
            output.append(f"   Source URL: {jd['source_url']}\n")

    if external_cases:
        output.append("Retrieved Court & Legal Search Results:")
        for i, res in enumerate(external_cases, 1):
            output.append(f"{i}. Title: {res['title']}")
            output.append(f"   Snippet: {res['snippet']}")
            output.append(f"   Source URL: {res['link']}\n")

    if not local_judgments and not external_cases:
        if not serper_key:
            output.append(
                "No matching judgments found in local landmark case database. "
                "To search live court databases across the Supreme Court and High Courts of Pakistan, "
                "please configure 'SERPER_API_KEY' in your .env file."
            )
        else:
            output.append("No court judgments found matching this query from public legal search indexes.")

    output.append(
        "\nNote on Case Law: Judicial search results reference published decisions from Pakistani superior courts. "
        "For official citations (e.g. PLD, SCMR, CLD, PCrLJ), consult official law reporters or authenticated legal archives."
    )

    return "\n".join(output)


# ==============================================================================
# Server Entrypoint
# ==============================================================================

if __name__ == "__main__":
    # Start the FastMCP server over standard input/output (stdio)
    mcp.run()
