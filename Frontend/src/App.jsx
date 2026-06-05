import { useState } from "react";
import axios from "axios";

function App() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);

  const analyzeImage = async () => {
    if (!file) {
      alert("Seleccione una imagen");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post(
        "http://localhost:8000/analyze",
        formData
      );

      setResult(response.data);

    } catch (error) {
      console.error(error);
      alert("Error conectando con FastAPI");
    }
  };

  return (
    <div style={{ padding: "40px" }}>
      <h1>DeepFake Detector</h1>

      <input
        type="file"
        accept="image/*"
        onChange={(e) => setFile(e.target.files[0])}
      />

      <br />
      <br />

      <button onClick={analyzeImage}>
        Analizar
      </button>

      {result && (
        <div style={{ marginTop: "20px" }}>
          <h2>Resultado</h2>

          <p>
            Predicción: {result.prediction}
          </p>

          <p>
            Confianza: {result.confidence}%
          </p>
        </div>
      )}
    </div>
  );
}

export default App;