document.getElementById('symptom-form').addEventListener('submit', function(event) {
    event.preventDefault();

    const symptoms = document.getElementById('symptoms').value.trim();
    const duration = document.getElementById('duration').value.trim();
    const language = document.getElementById('language').value;
    const outputType = document.getElementById('output-type').value;
    const submitBtn = document.getElementById('submit-btn');

    if (!symptoms || !duration || !language || !outputType) {
        alert('Please fill in all required fields.');
        return;
    }

    submitBtn.disabled = true;
    submitBtn.innerText = 'Processing...';

    const data = {
        symptoms: symptoms,
        duration: duration,
        language: language,
        output_type: outputType,
        answered_symptoms: [],
        additional_answers: {}
    };

    checkSymptoms(data);
});

function checkSymptoms(data) {
    const submitBtn = document.getElementById('submit-btn');
    fetch('/check_symptoms', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(responseData => {
        submitBtn.disabled = false;
        submitBtn.innerText = 'Submit';

        const resultDiv = document.getElementById('result');
        const questionsDiv = document.getElementById('questions');
        const medicineDiv = document.getElementById('medicine');
        resultDiv.style.display = 'none';
        questionsDiv.style.display = 'none';
        medicineDiv.style.display = 'none';

        if (responseData.error) {
            resultDiv.innerText = responseData.error;
            resultDiv.style.display = 'block';
            return;
        }

        if (responseData.text_result) {
            resultDiv.innerText = responseData.text_result;
            resultDiv.style.display = 'block';
        }

        if (responseData.audio_url) {
            const audio = new Audio(responseData.audio_url);
            audio.play();
        }

        if (responseData.next_question) {
            questionsDiv.innerHTML = '';
            const questionP = document.createElement('p');
            questionP.innerText = responseData.next_question;
            const yesBtn = document.createElement('button');
            yesBtn.innerText = 'Yes';
            yesBtn.className = 'btn btn-primary';
            yesBtn.onclick = () => answerQuestion(responseData.next_symptom, 'yes', data);
            const noBtn = document.createElement('button');
            noBtn.innerText = 'No';
            noBtn.className = 'btn btn-secondary';
            noBtn.onclick = () => answerQuestion(responseData.next_symptom, 'no', data);
            questionsDiv.appendChild(questionP);
            questionsDiv.appendChild(yesBtn);
            questionsDiv.appendChild(noBtn);
            questionsDiv.style.display = 'block';
        }

        if (responseData.medicine_question) {
            medicineDiv.innerHTML = '';
            const medicineP = document.createElement('p');
            medicineP.innerText = responseData.medicine_question;
            const yesBtn = document.createElement('button');
            yesBtn.innerText = 'Yes';
            yesBtn.className = 'btn btn-primary';
            yesBtn.onclick = () => answerMedicine('yes', data);
            const noBtn = document.createElement('button');
            noBtn.innerText = 'No';
            noBtn.className = 'btn btn-secondary';
            noBtn.onclick = () => answerMedicine('no', data);
            medicineDiv.appendChild(medicineP);
            medicineDiv.appendChild(yesBtn);
            medicineDiv.appendChild(noBtn);
            medicineDiv.style.display = 'block';
        }
    })
    .catch(error => {
        submitBtn.disabled = false;
        submitBtn.innerText = 'Submit';
        const resultDiv = document.getElementById('result');
        resultDiv.innerText = 'An error occurred. Please try again.';
        resultDiv.style.display = 'block';
    });
}

function answerQuestion(symptom, answer, previousData) {
    const additionalAnswers = previousData.additional_answers || {};
    additionalAnswers[symptom] = answer;

    const answeredSymptoms = previousData.answered_symptoms || [];
    answeredSymptoms.push(symptom);

    const data = {
        symptoms: previousData.symptoms,
        duration: previousData.duration,
        language: previousData.language,
        output_type: previousData.output_type,
        answered_symptoms: answeredSymptoms,
        additional_answers: additionalAnswers
    };

    checkSymptoms(data);
}

function answerMedicine(answer, previousData) {
    const data = {
        symptoms: previousData.symptoms,
        duration: previousData.duration,
        language: previousData.language,
        output_type: previousData.output_type,
        answered_symptoms: previousData.answered_symptoms || [],
        additional_answers: previousData.additional_answers || {},
        wants_medicine: answer
    };

    checkSymptoms(data);
}

document.getElementById('voice-btn').addEventListener('click', function() {
    const voiceInputBox = document.getElementById('voice-input-box');
    const voiceStatus = document.getElementById('voice-status');
    const symptomsInput = document.getElementById('symptoms');

    voiceInputBox.style.display = 'block';
    voiceStatus.innerText = 'Listening...';

    fetch('/voice_input', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        voiceInputBox.style.display = 'none';
        if (data.error) {
            voiceStatus.innerText = data.error;
            return;
        }
        symptomsInput.value = data.symptoms;
        voiceStatus.innerText = 'Symptoms captured successfully!';
    })
    .catch(error => {
        voiceInputBox.style.display = 'none';
        voiceStatus.innerText = 'An error occurred. Please try again.';
    });
});