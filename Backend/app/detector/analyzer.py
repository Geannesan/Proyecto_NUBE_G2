import cv2
import numpy as np


def analyze_image(image_path):

    evidence = []


    # Leer imagen

    image = cv2.imread(image_path)


    if image is None:

        return [
            "No se pudo leer la imagen"
        ]



    # Convertir a escala de grises

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )



    # =================================
    # Analisis de nitidez / detalles
    # =================================

    detail_score = cv2.Laplacian(
        gray,
        cv2.CV_64F
    ).var()



    if detail_score < 100:

        evidence.append(
            "La imagen presenta baja variación de detalles, posible característica de contenido sintético"
        )

    else:

        evidence.append(
            "La imagen presenta una distribución normal de detalles"
        )



    # =================================
    # Analisis de ruido
    # =================================

    mean, std = cv2.meanStdDev(
        gray
    )


    noise_level = std[0][0]



    if noise_level < 25:

        evidence.append(
            "Se detectó poca variación de ruido visual"
        )

    else:

        evidence.append(
            "La imagen presenta variaciones naturales de ruido"
        )



    # =================================
    # Analisis de bordes
    # =================================

    edges = cv2.Canny(
        gray,
        100,
        200
    )



    edge_ratio = (
        np.count_nonzero(edges)
        /
        edges.size
    )



    if edge_ratio < 0.05:

        evidence.append(
            "La imagen presenta pocos patrones estructurales"
        )

    else:

        evidence.append(
            "La imagen contiene suficientes detalles estructurales"
        )



    return evidence