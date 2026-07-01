function showStep(stepNumber) {

    // Hide every step

    const steps = document.querySelectorAll(".wizard-step");

    steps.forEach(step => {
        step.classList.add("hidden");
    });

    if(stepNumber === 0){

        document
            .getElementById("welcome-screen")
            .classList
            .remove("hidden");

    }

    else{

        document
            .getElementById("step" + stepNumber)
            .classList
            .remove("hidden");

    }

}