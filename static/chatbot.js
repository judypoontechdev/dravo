// ==========================================
// Example Question Buttons
// ==========================================

document.querySelectorAll(".example-question").forEach(button => {

    button.addEventListener("click", function () {

        document.getElementById("ai-question").value = this.innerText;

    });

});


// ==========================================
// Ask AI Button
// ==========================================

document.getElementById("ask-ai").addEventListener("click", async function () {

    const question = document.getElementById("ai-question").value.trim();

    if (question === "") {

        alert("Please enter a question.");

        return;

    }

    const answerBox = document.getElementById("ai-answer");

    answerBox.innerHTML = `
        <span class="text-secondary">
            🤖 Thinking...
        </span>
    `;

    try {

        const response = await fetch("/chat", {

            method: "POST",

            headers: {

                "Content-Type": "application/json"

            },

            body: JSON.stringify({

                question: question

            })

        });

        const data = await response.json();

        if (response.ok) {

            answerBox.innerHTML = `
                <div class="alert alert-success mb-0">
                    ${data.answer}
                </div>
            `;

        }

        else {

            answerBox.innerHTML = `
                <div class="alert alert-danger mb-0">
                    ${data.error}
                </div>
            `;

        }

    }

    catch (error) {

        answerBox.innerHTML = `
            <div class="alert alert-danger mb-0">
                Failed to connect to the server.
            </div>
        `;

        console.error(error);

    }

});