const generateTokenButton = document.getElementById("generate-token-button");
const tokenNameInput = document.getElementById("collector-name")
const generatedTokenValue = document.getElementById("generated-token-value")

generateTokenButton.addEventListener('click', async () => {
    const response = await fetch("/api/generate_token", {
        method: 'POST',
        headers: {
        'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            name: tokenNameInput.value
        }),
    });

    const result = await response.json();

    if (result.error) {
        alert(result.error)
        return;
    }

    generatedTokenValue.value = result.generated_token;
});