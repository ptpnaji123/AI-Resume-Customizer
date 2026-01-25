import requests
from bs4 import BeautifulSoup


def scrape_job_description(url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove unwanted tags
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator="\n")

    # Clean extra blank lines
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    clean_text = "\n".join(lines)

    return clean_text


if __name__ == "__main__":
    # TEMP test
    job_url = "https://careers-inc.nttdata.com/job/Bengaluru-Information-Security-Operations-Specialist-Advisor-Cybersecurity-Delivery-Projects-KA/1357985700/"
    jd_text = scrape_job_description(job_url)
    print(jd_text[:6500])
