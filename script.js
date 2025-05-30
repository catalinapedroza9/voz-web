let mediaRecorder;
let audioChunks = [];

// Obtener referencias a los elementos del DOM
const startBtn = document.getElementById("start");
const stopBtn = document.getElementById("stop");
const applyBtn = document.getElementById("apply-eq");
const resetBtn = document.getElementById("reset"); // Botón de reiniciar
const status = document.getElementById("status");
const audioOriginal = document.getElementById("audio-original");
const audioProcesado = document.getElementById("audio-procesado");

// Funcionalidad para grabar audio
startBtn.onclick = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];

    mediaRecorder.ondataavailable = e => audioChunks.push(e.data);

    mediaRecorder.onstart = () => {
        status.textContent = "🎙️ Grabando...";
        startBtn.disabled = true;
        stopBtn.disabled = false;
        applyBtn.disabled = true;
    };

    mediaRecorder.onstop = () => {
        const blob = new Blob(audioChunks, { type: "audio/webm" });
        audioOriginal.src = URL.createObjectURL(blob);
        status.textContent = "🎧 Grabación lista. Ahora aplica el ecualizador.";
        startBtn.disabled = false;
        stopBtn.disabled = true;
        applyBtn.disabled = false;
    };

    mediaRecorder.start();
};

// Funcionalidad para detener la grabación
stopBtn.onclick = () => {
    if (mediaRecorder && mediaRecorder.state === "recording") {
        mediaRecorder.stop();
    }
};

// Funcionalidad para aplicar el ecualizador
applyBtn.onclick = async () => {
    if (!audioChunks.length) {
        alert("Graba primero antes de aplicar el ecualizador.");
        return;
    }

    status.textContent = "⏳ Procesando...";

    const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
    const formData = new FormData();
    formData.append("audio", audioBlob, "grabacion.webm");

    for (let i = 0; i < 10; i++) {
        const val = document.getElementById(`band-${i}`).value;
        formData.append(`band_${i}`, val);
    }

    try {
        const res = await fetch("https://voz-backend.onrender.com/", {
            method: "POST",
            body: formData
        });

        const result = await res.json();

        if (res.ok) {
            status.textContent = "✅ Procesado correctamente.";
            audioProcesado.src = "https://voz-backend.onrender.com/" + Date.now();
        } else {
            status.textContent = "❌ Error: " + result.error;
        }
    } catch (err) {
        console.error(err);
        status.textContent = "❌ Error al conectar con el backend.";
    }
};

// Funcionalidad para reiniciar los deslizadores y el estado del ecualizador
resetBtn.onclick = async () => {
    try {
        const res = await fetch("https://voz-backend.onrender.com/", {
    method: "POST",
    headers: {
        "Content-Type": "application/json"
    },
    body: JSON.stringify({}) // 🛠️ esta línea es clave
});
        const result = await res.json();
        alert(result.mensaje || result.error);

        // Reiniciar los deslizadores a 0 dB
        for (let i = 0; i < 10; i++) {
            const slider = document.getElementById(`band-${i}`);
            slider.value = 0; // Restablecer el valor del slider a 0
            const valueDisplay = document.getElementById(`value-${i}`);
            valueDisplay.textContent = "0 dB"; // Actualizar la visualización del valor
        }

        // Reiniciar el estado de los botones
        startBtn.disabled = false;
        stopBtn.disabled = true;
        applyBtn.disabled = true;
        status.textContent = "Presiona grabar para comenzar";

    } catch (err) {
        console.error(err);
        alert("❌ Error al conectar con el backend.");
    }
};

// Mostrar valores de dB en tiempo real junto a los sliders
for (let i = 0; i < 10; i++) {
    const slider = document.getElementById(`band-${i}`);
    const label = document.getElementById(`value-${i}`);
    // Mostrar valor inicial
    label.textContent = `${slider.value} dB`;
    slider.addEventListener("input", () => {
        label.textContent = `${slider.value} dB`;
    });
}
