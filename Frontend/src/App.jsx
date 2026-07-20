import { useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import "./App.css";

const API_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000";

/*
  Rutas usadas por cada botón.

  La opción Imagen + AI Image Detector conserva tu ruta actual:
  POST http://localhost:8000/analyze

  Puedes cambiar cualquiera de las otras rutas aquí o mediante
  variables VITE_* en tu archivo .env.
*/
const ENDPOINTS = {
  image: {
    ai: "/api/v1/image/analyze",
    deepfake: "/api/v1/image/analyze",
  },
  audio: {
    ai: "/api/v1/audio/analyze",
    deepfake: "/api/v1/audio/analyze",
  },
  video: {
    ai: "/api/v1/video/analyze",
    deepfake: "/api/v1/video/analyze",
  },
};

const MEDIA_CONFIG = {
  audio: {
    label: "AUDIO",
    accept: "audio/*",
    uploadTitle: "Suelta tu audio aquí",
    uploadText:
      "o haz clic para seleccionar un archivo de audio y verificarlo al instante",
    loadingTitle: "Analizando audio...",
    loadingText:
      "El modelo inspecciona la voz, frecuencias, artefactos y patrones de síntesis.",
    previewLabel: "Audio seleccionado",
  },
  image: {
    label: "IMAGEN",
    accept: "image/*",
    uploadTitle: "Suelta tu imagen aquí",
    uploadText:
      "o haz clic para seleccionar una imagen y verificarla al instante",
    loadingTitle: "Analizando imagen...",
    loadingText:
      "El modelo inspecciona patrones visuales, texturas, compresión y posibles evidencias de manipulación.",
    previewLabel: "Imagen seleccionada",
  },
  video: {
    label: "VIDEO",
    accept: "video/*",
    uploadTitle: "Suelta tu video aquí",
    uploadText:
      "o haz clic para seleccionar un video y verificarlo al instante",
    loadingTitle: "Analizando video...",
    loadingText:
      "El modelo inspecciona fotogramas, sincronización, rostros, movimiento y posibles alteraciones.",
    previewLabel: "Video seleccionado",
  },
};

const DETECTOR_CONFIG = {
  audio: {
    ai: "AI Audio Detector",
    deepfake: "Voice Deepfake Detector",
  },
  image: {
    ai: "AI Image Detector",
    deepfake: "Deepfake Detector",
  },
  video: {
    ai: "AI Video Detector",
    deepfake: "Video Deepfake Detector",
  },
};

function ShieldIcon() {
  return (
    <svg
      viewBox="0 0 48 48"
      aria-hidden="true"
      className="brand-icon"
    >
      <path
        d="M24 4 40 10v12c0 10.4-6.4 17.7-16 22C14.4 39.7 8 32.4 8 22V10L24 4Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="3"
      />
      <rect
        x="17"
        y="21"
        width="14"
        height="11"
        rx="2.5"
        fill="currentColor"
      />
      <path
        d="M20 21v-3.2a4 4 0 0 1 8 0V21"
        fill="none"
        stroke="currentColor"
        strokeWidth="3"
      />
      <circle cx="24" cy="26.5" r="1.4" fill="#111d38" />
    </svg>
  );
}

function UploadIcon() {
  return (
    <svg viewBox="0 0 64 64" aria-hidden="true">
      <path
        d="M32 43V13m0 0L20.5 24.5M32 13l11.5 11.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M13 40v9a4 4 0 0 0 4 4h30a4 4 0 0 0 4-4v-9"
        fill="none"
        stroke="currentColor"
        strokeWidth="5"
        strokeLinecap="round"
      />
    </svg>
  );
}

function CameraIcon() {
  return (
    <svg viewBox="0 0 48 48" aria-hidden="true">
      <path
        d="M8 15h8l3-5h10l3 5h8a4 4 0 0 1 4 4v17a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4V19a4 4 0 0 1 4-4Z"
        fill="currentColor"
      />
      <circle cx="24" cy="27" r="8" fill="#a9aaab" />
      <circle cx="24" cy="27" r="5" fill="currentColor" />
    </svg>
  );
}

function UserIcon() {
  return (
    <svg viewBox="0 0 48 48" aria-hidden="true">
      <circle
        cx="24"
        cy="17"
        r="8"
        fill="none"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        d="M8 41c1.5-9.2 7-14 16-14s14.5 4.8 16 14"
        fill="none"
        stroke="currentColor"
        strokeWidth="4"
        strokeLinecap="round"
      />
      <circle
        cx="24"
        cy="24"
        r="20"
        fill="none"
        stroke="currentColor"
        strokeWidth="3"
      />
    </svg>
  );
}

function CircuitGraphic({ className = "" }) {
  return (
    <svg
      className={`circuit-graphic ${className}`}
      viewBox="0 0 520 280"
      aria-hidden="true"
    >
      <g fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M0 38h122l28-28h90" />
        <path d="M0 67h180l29-29h116" />
        <path d="M0 96h220l30-30h180" />
        <path d="M0 126h145l30 30h172" />
        <path d="M0 160h240l28-28h177" />
        <path d="M0 195h155l34 34h170" />
        <path d="M0 230h245l26-26h153" />
        <path d="M328 0v42l31 31h109" />
        <path d="M382 0v24l42 42h96" />
        <path d="M438 0v51l26 26h56" />
      </g>

      <g fill="currentColor">
        <circle cx="122" cy="38" r="5" />
        <circle cx="180" cy="67" r="5" />
        <circle cx="220" cy="96" r="5" />
        <circle cx="145" cy="126" r="5" />
        <circle cx="240" cy="160" r="5" />
        <circle cx="155" cy="195" r="5" />
        <circle cx="245" cy="230" r="5" />
        <circle cx="359" cy="73" r="5" />
        <circle cx="424" cy="66" r="5" />
        <circle cx="464" cy="77" r="5" />
      </g>
    </svg>
  );
}

function NetworkGraphic({ className = "" }) {
  const nodes = [
    ["36", "45"],
    ["93", "65"],
    ["148", "47"],
    ["202", "86"],
    ["70", "112"],
    ["121", "111"],
    ["170", "125"],
    ["45", "168"],
    ["106", "183"],
    ["167", "205"],
    ["215", "169"],
  ];

  return (
    <svg
      className={`network-graphic ${className}`}
      viewBox="0 0 260 250"
      aria-hidden="true"
    >
      <g stroke="currentColor" strokeWidth="1.5" opacity="0.8">
        <line x1="36" y1="45" x2="93" y2="65" />
        <line x1="36" y1="45" x2="70" y2="112" />
        <line x1="93" y1="65" x2="148" y2="47" />
        <line x1="93" y1="65" x2="121" y2="111" />
        <line x1="148" y1="47" x2="202" y2="86" />
        <line x1="148" y1="47" x2="170" y2="125" />
        <line x1="70" y1="112" x2="121" y2="111" />
        <line x1="70" y1="112" x2="45" y2="168" />
        <line x1="121" y1="111" x2="170" y2="125" />
        <line x1="121" y1="111" x2="106" y2="183" />
        <line x1="170" y1="125" x2="202" y2="86" />
        <line x1="170" y1="125" x2="215" y2="169" />
        <line x1="45" y1="168" x2="106" y2="183" />
        <line x1="106" y1="183" x2="167" y2="205" />
        <line x1="167" y1="205" x2="215" y2="169" />
        <line x1="106" y1="183" x2="170" y2="125" />
        <line x1="93" y1="65" x2="70" y2="112" />
        <line x1="121" y1="111" x2="148" y2="47" />
      </g>

      <g fill="currentColor">
        {nodes.map(([cx, cy]) => (
          <circle
            key={`${cx}-${cy}`}
            cx={cx}
            cy={cy}
            r="8"
          />
        ))}
      </g>
    </svg>
  );
}

function App() {
  const [activeMedia, setActiveMedia] = useState("image");
  const [activeDetector, setActiveDetector] =
    useState("ai");
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [dragging, setDragging] = useState(false);

  const fileInputRef = useRef(null);

  const media = MEDIA_CONFIG[activeMedia];
  const detectorLabels = DETECTOR_CONFIG[activeMedia];
  const currentEndpoint =
    ENDPOINTS[activeMedia][activeDetector];

  useEffect(() => {
    return () => {
      if (preview) {
        URL.revokeObjectURL(preview);
      }
    };
  }, [preview]);

  const confidence = useMemo(() => {
    const rawValue = Number(result?.confidence ?? 0);

    if (!Number.isFinite(rawValue)) {
      return 0;
    }

    const percentage =
      rawValue > 0 && rawValue <= 1
        ? rawValue * 100
        : rawValue;

    return Math.min(100, Math.max(0, percentage));
  }, [result]);

  const clearCurrentFile = () => {
    if (preview) {
      URL.revokeObjectURL(preview);
    }

    setFile(null);
    setPreview("");
    setResult(null);
    setDragging(false);

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const selectMedia = (mediaType) => {
    if (mediaType === activeMedia) return;

    clearCurrentFile();
    setActiveMedia(mediaType);
    setActiveDetector("ai");
  };

  const selectDetector = (detectorType) => {
    if (detectorType === activeDetector) return;

    setActiveDetector(detectorType);
    setResult(null);
  };

  const handleFile = (selectedFile) => {
    if (!selectedFile) return;

    const expectedType = `${activeMedia}/`;

    if (!selectedFile.type.startsWith(expectedType)) {
      alert(
        `El archivo seleccionado debe ser de tipo ${media.label.toLowerCase()}.`
      );
      return;
    }

    if (preview) {
      URL.revokeObjectURL(preview);
    }

    setFile(selectedFile);
    setPreview(URL.createObjectURL(selectedFile));
    setResult(null);
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setDragging(false);
    handleFile(event.dataTransfer.files?.[0]);
  };

  const analyzeFile = async () => {
    if (!file) {
      fileInputRef.current?.click();
      return;
    }

    const formData = new FormData();

    formData.append("file", file);
    formData.append("media_type", activeMedia);
    formData.append("detector_type", activeDetector);

    try {
      setLoading(true);
      setResult(null);

      const response = await axios.post(
        `${API_URL}${currentEndpoint}`,
        formData
      );

      setResult(response.data);
    } catch (error) {
      console.error("Error completo:", error);
      console.error("Respuesta backend:", error.response?.data);

      const backendDetail =
        error.response?.data?.detail ||
        error.message ||
        "Error desconocido";

      const status =
        error.response?.status ||
        "Sin respuesta";

      alert(
        `No fue posible completar el análisis.\n\n` +
        `Estado: ${status}\n` +
        `Ruta utilizada: ${currentEndpoint}\n` +
        `Detalle: ${backendDetail}`
      );
    } finally {
      setLoading(false);
    }
  };

  const resultClass = () => {
    const prediction = String(
      result?.prediction ??
        result?.label ??
        result?.result ??
        ""
    ).toLowerCase();

    if (
      prediction.includes("inconclusive") ||
      prediction.includes("no concluyente")
    ) {
      return "inconclusive";
    }

    return prediction.includes("fake") ||
      prediction.includes("ai") ||
      prediction.includes("ia") ||
      prediction.includes("falso") ||
      prediction.includes("manipulado")
      ? "fake"
      : "real";
  };

  const rawPredictionText =
    result?.prediction ??
    result?.label ??
    result?.result ??
    "Resultado recibido";

  const predictionText =
    String(rawPredictionText).toUpperCase() ===
    "INCONCLUSIVE"
      ? "NO CONCLUYENTE"
      : rawPredictionText;

  const modelReason =
    result?.analysis?.model_reason ??
    result?.model_reason ??
    result?.analysis ??
    "El backend no devolvió una explicación adicional.";

  const evidence = Array.isArray(
    result?.analysis?.evidence
  )
    ? result.analysis.evidence
    : Array.isArray(result?.evidence)
      ? result.evidence
      : [];

  const renderPreview = () => {
    if (!preview) return null;

    if (activeMedia === "image") {
      return (
        <img
          src={preview}
          className="preview preview-image"
          alt={media.previewLabel}
        />
      );
    }

    if (activeMedia === "audio") {
      return (
        <audio
          className="preview preview-audio"
          src={preview}
          controls
          onClick={(event) => event.stopPropagation()}
        >
          Tu navegador no soporta la reproducción de audio.
        </audio>
      );
    }

    return (
      <video
        className="preview preview-video"
        src={preview}
        controls
        onClick={(event) => event.stopPropagation()}
      >
        Tu navegador no soporta la reproducción de video.
      </video>
    );
  };

  return (
    <main className="page">
      <div className="polygon polygon--left" />
      <div className="polygon polygon--right" />

      <CircuitGraphic className="circuit-graphic--top" />
      <CircuitGraphic className="circuit-graphic--bottom" />
      <NetworkGraphic className="network-graphic--left" />
      <NetworkGraphic className="network-graphic--right" />

      <div className="content">
        <header className="hero">
          <div className="brand">
            <ShieldIcon />
            <h1>DeepFakeShield</h1>
          </div>

          <p>
            Plataforma inteligente para detectar y verificar
            contenido manipulado o generado mediante inteligencia
            artificial.
          </p>
        </header>

        <section className="detector-shell">
          <nav
            className="media-switch"
            aria-label="Tipo de contenido"
          >
            {Object.keys(MEDIA_CONFIG).map((mediaType) => (
              <button
                key={mediaType}
                type="button"
                className={
                  activeMedia === mediaType ? "active" : ""
                }
                aria-pressed={activeMedia === mediaType}
                onClick={() => selectMedia(mediaType)}
              >
                {MEDIA_CONFIG[mediaType].label}
              </button>
            ))}
          </nav>

          <nav
            className="sub-switch"
            aria-label="Tipo de detector"
          >
            <button
              type="button"
              className={
                activeDetector === "ai" ? "active" : ""
              }
              aria-pressed={activeDetector === "ai"}
              onClick={() => selectDetector("ai")}
            >
              {detectorLabels.ai}
            </button>

            <button
              type="button"
              className={
                activeDetector === "deepfake"
                  ? "active"
                  : ""
              }
              aria-pressed={
                activeDetector === "deepfake"
              }
              onClick={() => selectDetector("deepfake")}
            >
              {detectorLabels.deepfake}
            </button>
          </nav>

          <section className="metal-panel">
            <span className="screw screw--tl" />
            <span className="screw screw--tr" />
            <span className="screw screw--bl" />
            <span className="screw screw--br" />

            <div
              className="device-controls"
              aria-hidden="true"
            >
              <span className="status-light" />
              <CameraIcon />
              <UserIcon />
            </div>

            <div
              className={`drop-area ${
                dragging ? "dragging" : ""
              } ${file ? "has-file" : ""}`}
              onClick={() =>
                fileInputRef.current?.click()
              }
              onDragOver={(event) => {
                event.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
              role="button"
              tabIndex={0}
              onKeyDown={(event) => {
                if (
                  event.key === "Enter" ||
                  event.key === " "
                ) {
                  fileInputRef.current?.click();
                }
              }}
            >
              <input
                ref={fileInputRef}
                key={`${activeMedia}-${activeDetector}`}
                type="file"
                accept={media.accept}
                onChange={(event) =>
                  handleFile(event.target.files?.[0])
                }
              />

              {preview ? (
                <div
                  className="preview-wrap"
                  onClick={(event) =>
                    event.stopPropagation()
                  }
                >
                  {renderPreview()}

                  <span className="file-name">
                    {file?.name}
                  </span>

                  <button
                    type="button"
                    className="change-file-button"
                    onClick={(event) => {
                      event.stopPropagation();
                      fileInputRef.current?.click();
                    }}
                  >
                    Cambiar archivo
                  </button>
                </div>
              ) : (
                <>
                  <div className="upload-icon">
                    <UploadIcon />
                  </div>

                  <h2>{media.uploadTitle}</h2>
                  <p>{media.uploadText}</p>
                </>
              )}

              <button
                type="button"
                className="primary-button"
                onClick={(event) => {
                  event.stopPropagation();
                  analyzeFile();
                }}
                disabled={loading}
              >
                {loading ? (
                  <>
                    <span className="button-spinner" />
                    Analizando...
                  </>
                ) : (
                  "Comprobar Autenticidad"
                )}
              </button>
            </div>
          </section>

          <div className="selected-mode" aria-live="polite">
            <span>{media.label}</span>
            <strong>
              {detectorLabels[activeDetector]}
            </strong>
          </div>

          {loading && (
            <section
              className="processing-card"
              aria-live="polite"
            >
              <div className="scanner-line" />
              <h2>{media.loadingTitle}</h2>
              <p>{media.loadingText}</p>
            </section>
          )}

          {result && (
            <section
              className={`result-card ${resultClass()}`}
              aria-live="polite"
            >
              <div className="result-heading">
                <div>
                  <span className="eyebrow">
                    RESULTADO DEL ANÁLISIS
                  </span>
                  <h2>{predictionText}</h2>
                </div>

                <div
                  className="confidence-ring"
                  style={{
                    "--confidence": `${confidence * 3.6}deg`,
                  }}
                >
                  <span>
                    {confidence.toFixed(0)}%
                  </span>
                </div>
              </div>

              <div className="confidence-block">
                <div className="confidence-label">
                  <span>Nivel de confianza</span>
                  <strong>
                    {confidence.toFixed(1)}%
                  </strong>
                </div>

                <div className="confidence-bar">
                  <div
                    className="confidence-progress"
                    style={{
                      width: `${confidence}%`,
                    }}
                  />
                </div>
              </div>

              <div className="model-analysis">
                <h3>Explicación del modelo</h3>
                <p>
                  {typeof modelReason === "string"
                    ? modelReason
                    : JSON.stringify(modelReason)}
                </p>
              </div>

              {evidence.length > 0 && (
                <div className="evidence-section">
                  <h3>Indicadores encontrados</h3>

                  <div className="evidence-grid">
                    {evidence.map((item, index) => (
                      <article
                        className="evidence-card"
                        key={`${String(item)}-${index}`}
                      >
                        <span className="evidence-check">
                          ✓
                        </span>
                        <p>
                          {typeof item === "string"
                            ? item
                            : JSON.stringify(item)}
                        </p>
                      </article>
                    ))}
                  </div>
                </div>
              )}
            </section>
          )}
        </section>

        <section className="technology-strip">
          <nav className="technology-tabs">
            <button type="button" className="active">
              TECNOLOGÍAS
            </button>
            <button type="button">
              MONITOREO IA
            </button>
            <button type="button">
              DEEP FAKE DETECTOR
            </button>
            <button type="button">
              SEGURIDAD
            </button>
          </nav>

          <p>
            AI Image Detector • Automatización • Deepfake
            Detector • Autenticidad Digital • Detección de
            Manipulación • Análisis de Patrones •
            Verificación de Contenido
          </p>
        </section>
      </div>

    

      <footer className="footer">
        <div className="footer-links">
          <a href="#deep-links">🇪🇨 Deep Links</a>
          <a href="#contacts">Contactos</a>
          <a href="#privacy">Privacidad</a>
          <a href="#terms">Términos</a>
        </div>
      </footer>
    </main>
  );
}

export default App;