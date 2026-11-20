
const output = document.getElementById('log-output');
const refreshButton = document.getElementById('refresh')
const searchInput = document.getElementById('query')
const submitSearch = document.getElementById('submit-search')

let logText = "";

async function loadLog() {
    const response = await fetch("/api/discover/log");
    logText = await response.text();
    output.textContent = logText;
}

loadLog()

submitSearch.addEventListener('click', () => {
    const query = searchInput.value.trim();
    const matches = logText
        .split(/\r?\n/)
        .filter(line => line.includes(query));

    output.textContent = matches.length
        ? matches.join("\n")
        : "No matches found";
})

refreshButton.addEventListener('click', () => {
    loadLog()
})