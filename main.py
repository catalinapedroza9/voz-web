from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.io import wavfile
from scipy.signal import butter, sosfilt, spectrogram
from pydub import AudioSegment

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

CARPETA = "backend"
RUTA_ORIGINAL = os.path.join(CARPETA, "recibido.wav")
RUTA_PROCESADO = os.path.join(CARPETA, "procesado.wav")
RUTA_SPECTRO_ORIGINAL = os.path.join(CARPETA, "original_spectrogram.png")
RUTA_SPECTRO_PROCESADO = os.path.join(CARPETA, "procesado_spectrogram.png")
os.makedirs(CARPETA, exist_ok=True)

BANDAS = [(20, 44), (45, 88), (89, 177), (178, 355), (356, 710),
          (711, 1420), (1421, 2840), (2841, 5680), (5681, 11360), (11361, 20000)]

def generar_spectrograma(ruta_audio, ruta_img):
    framerate, signal = wavfile.read(ruta_audio)
    if signal.ndim > 1:
        signal = signal[:, 0]
    plt.figure(figsize=(10, 4))
    Pxx, freqs, bins, im = plt.specgram(signal, Fs=framerate, NFFT=1024, noverlap=512, cmap="plasma")
    plt.clim(-100, 0)
    plt.colorbar(label='dB')
    plt.title("Espectrograma")
    plt.tight_layout()
    plt.savefig(ruta_img)
    plt.close()

def calcular_datos_spectrograma(ruta_audio):
    framerate, signal = wavfile.read(ruta_audio)
    if signal.ndim > 1:
        signal = signal[:, 0]
    f, t, Sxx = spectrogram(signal, fs=framerate, nperseg=1024, noverlap=512)
    Sxx_log = 10 * np.log10(Sxx + 1e-10)
    return {
        "frecuencias": f.tolist(),
        "tiempos": t.tolist(),
        "amplitudes": Sxx_log.tolist()
    }

def butter_bandpass_sos(lowcut, highcut, fs, order=4):
    nyq = fs / 2
    low = max(lowcut / nyq, 1e-5)
    high = min(highcut / nyq, 0.9999)
    if low >= high:
        high = low + 1e-4
    return butter(order, [low, high], btype='band', output='sos')

def aplicar_ecualizador(data, fs, ganancias_db):
    data = data.astype(np.float64) / 32768.0  # normalización a -1.0 a 1.0
    procesado = np.zeros_like(data)
    
    # Convertir ganancias de dB a factores lineales
    ganancias_lineales = [10 ** (g / 20) for g in ganancias_db]

    # Aumentar el rango de ganancias para hacer cambios más notables
    ganancias_lineales = [g * 2 for g in ganancias_lineales]  # Aumentar el factor

    # Sumar las bandas filtradas con sus ganancias
    for i, (low, high) in enumerate(BANDAS):
        sos = butter_bandpass_sos(low, high, fs)
        filtrada = sosfilt(sos, data)
        procesado += filtrada * ganancias_lineales[i]

    # Normalizar para evitar clipping
    max_abs = np.max(np.abs(procesado))
    if max_abs > 1.0:
        procesado /= max_abs

    procesado = np.nan_to_num(procesado)
    procesado = np.clip(procesado, -1.0, 1.0)
    return np.int16(procesado * 32767)

@app.post("/aplicar-ecualizador")
async def aplicar_ecualizador_endpoint(
    audio: UploadFile = File(...),
    band_0: int = Form(...),
    band_1: int = Form(...),
    band_2: int = Form(...),
    band_3: int = Form(...),
    band_4: int = Form(...),
    band_5: int = Form(...),
    band_6: int = Form(...),
    band_7: int = Form(...),
    band_8: int = Form(...),
    band_9: int = Form(...)
):
    try:
        print("📥 Recibiendo audio...")
        contents = await audio.read()
        ruta_temporal = os.path.join(CARPETA, "temporal.webm")
        with open(ruta_temporal, "wb") as f:
            f.write(contents)
        print("✅ Audio guardado temporalmente.")

        print("🎧 Convirtiendo .webm a .wav con pydub...")
        audio_segment = AudioSegment.from_file(ruta_temporal, format="webm")
        audio_segment.export(RUTA_ORIGINAL, format="wav")
        print("✅ Conversión completada.")

        print("📊 Leyendo .wav original...")
        fs, data = wavfile.read(RUTA_ORIGINAL)
        if data.ndim > 1:
            data = data[:, 0]
        print(f"✅ Audio cargado con sample rate: {fs} Hz")

        bandas_db = [band_0, band_1, band_2, band_3, band_4,
                     band_5, band_6, band_7, band_8, band_9]
        print("🎚️ Ganancias recibidas:", bandas_db)

        print("🔄 Aplicando ecualizador...")
        data_filtrada = aplicar_ecualizador(data, fs, bandas_db)
        wavfile.write(RUTA_PROCESADO, fs, data_filtrada)
        print("✅ Audio procesado y guardado.")

        print("📷 Generando espectrogramas...")
        generar_spectrograma(RUTA_ORIGINAL, RUTA_SPECTRO_ORIGINAL)
        generar_spectrograma(RUTA_PROCESADO, RUTA_SPECTRO_PROCESADO)
        print("✅ Espectrogramas generados.")

        return {"mensaje": "Audio procesado correctamente."}

    except Exception as e:
        print("❌ Error durante el procesamiento:", str(e))
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/reiniciar")
async def reiniciar():
    try:
        # Eliminar archivos procesados
        if os.path.exists(RUTA_PROCESADO):
            os.remove(RUTA_PROCESADO)
        if os.path.exists(RUTA_SPECTRO_PROCESADO):
            os.remove(RUTA_SPECTRO_PROCESADO)
        
        return {"mensaje": "Ecualizador reiniciado correctamente."}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/audio-original")
def audio_original():
    return FileResponse(RUTA_ORIGINAL, media_type="audio/wav")

@app.get("/audio-procesado")
def audio_procesado():
    return FileResponse(RUTA_PROCESADO, media_type="audio/wav")

@app.get("/spectrograma-original")
def spectrograma_original():
    return FileResponse(RUTA_SPECTRO_ORIGINAL, media_type="image/png")

@app.get("/spectrograma-procesado")
def spectrograma_procesado():
    return FileResponse(RUTA_SPECTRO_PROCESADO, media_type="image/png")

@app.get("/datos-spectrograma-original")
def datos_spectrograma_original():
    datos = calcular_datos_spectrograma(RUTA_ORIGINAL)
    return JSONResponse(content=datos)

@app.get("/datos-spectrograma-procesado")
def datos_spectrograma_procesado():
    datos = calcular_datos_spectrograma(RUTA_PROCESADO)
    return JSONResponse(content=datos)
