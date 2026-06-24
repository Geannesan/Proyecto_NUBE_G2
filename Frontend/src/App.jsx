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


    formData.append(
      "file",
      file
    );



    try {


      const response = await axios.post(

        "http://localhost:8000/analyze",

        formData

      );



      setResult(
        response.data
      );



    } catch (error) {


      console.error(error);

      alert(
        "Error conectando con FastAPI"
      );


    }

  };



  return (

    <div style={{ padding:"40px" }}>


      <h1>
        DeepFake Detector
      </h1>



      <input

        type="file"

        accept="image/*"

        onChange={
          (e)=>
          setFile(
            e.target.files[0]
          )
        }

      />



      <br />
      <br />



      <button onClick={analyzeImage}>

        Analizar

      </button>



      {
        result && (

          <div style={{
            marginTop:"30px",
            padding:"20px",
            border:"1px solid gray",
            borderRadius:"10px"
          }}>


            <h2>
              Resultado
            </h2>



            <p>

              Predicción:

              <b>
                {" "}
                {result.prediction}
              </b>

            </p>



            <p>

              Confianza:

              <b>
                {" "}
                {result.confidence}%

              </b>

            </p>




            <hr />



            <h2>
              Análisis de evidencia
            </h2>



            <p>

              {result.analysis.model_reason}

            </p>




            <h3>
              Indicadores encontrados:
            </h3>



            <ul>


              {
                result.analysis.evidence.map(

                  (item,index)=>(

                    <li key={index}>

                      {item}

                    </li>

                  )

                )
              }


            </ul>



          </div>

        )
      }



    </div>

  );


}


export default App;