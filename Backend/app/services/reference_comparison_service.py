import hashlib
from pathlib import Path

import cv2
import numpy as np


def compare_with_original(candidate_path: Path, reference_path: Path) -> dict:
    """Alinea un original y cuantifica cambios visibles en la misma escena."""
    candidate = cv2.imread(str(candidate_path), cv2.IMREAD_COLOR)
    reference = cv2.imread(str(reference_path), cv2.IMREAD_COLOR)
    if candidate is None or reference is None:
        raise ValueError("No se pudo decodificar la imagen o su referencia original.")

    candidate_gray = cv2.cvtColor(candidate, cv2.COLOR_BGR2GRAY)
    reference_gray = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)
    orb = cv2.ORB_create(nfeatures=5000)
    candidate_points, candidate_desc = orb.detectAndCompute(candidate_gray, None)
    reference_points, reference_desc = orb.detectAndCompute(reference_gray, None)
    if candidate_desc is None or reference_desc is None:
        raise ValueError("Las imágenes no contienen suficientes puntos para compararlas.")

    pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(
        reference_desc, candidate_desc, k=2
    )
    matches = [first for first, second in pairs if first.distance < 0.70 * second.distance]
    if len(matches) < 20:
        raise ValueError(
            "La referencia no parece corresponder a la misma escena o carece de detalle suficiente."
        )

    source = np.float32([reference_points[item.queryIdx].pt for item in matches])
    target = np.float32([candidate_points[item.trainIdx].pt for item in matches])
    transform, inliers = cv2.findHomography(source, target, cv2.RANSAC, 5.0)
    if transform is None:
        raise ValueError("No se pudo alinear la referencia con la imagen analizada.")

    height, width = candidate_gray.shape
    aligned = cv2.warpPerspective(reference, transform, (width, height))
    overlap = cv2.warpPerspective(
        np.ones(reference_gray.shape, dtype=np.uint8), transform, (width, height)
    ).astype(bool)
    overlap_percent = float(overlap.mean() * 100.0)
    if overlap_percent < 45.0:
        raise ValueError("La referencia coincide con una parte demasiado pequeña de la escena.")

    # Un desenfoque leve reduce diferencias de JPEG y conserva cambios de forma,
    # texto, vestuario y rostro que sí son relevantes para el cotejo.
    candidate_soft = cv2.GaussianBlur(candidate, (5, 5), 0)
    aligned_soft = cv2.GaussianBlur(aligned, (5, 5), 0)
    difference = cv2.cvtColor(
        cv2.absdiff(candidate_soft, aligned_soft), cv2.COLOR_BGR2GRAY
    )
    values = difference[overlap]
    mean_difference = float(values.mean())
    changed_25 = float(np.mean(values > 25) * 100.0)
    changed_50 = float(np.mean(values > 50) * 100.0)
    inlier_percent = float(
        (int(inliers.sum()) / max(1, len(matches))) * 100.0
    ) if inliers is not None else 0.0

    confirmed = (
        len(matches) >= 25
        and inlier_percent >= 25.0
        and mean_difference >= 15.0
        and changed_50 >= 8.0
    )
    confidence = min(
        99.0,
        max(0.0, 35.0 + mean_difference + changed_25 + changed_50),
    )

    return {
        "status": "changes_confirmed" if confirmed else "no_substantial_changes",
        "changes_confirmed": confirmed,
        "confidence": round(confidence, 2),
        "method": "ORB + homografía RANSAC + diferencia multirregional suavizada",
        "feature_matches": len(matches),
        "inlier_matches_percent": round(inlier_percent, 2),
        "overlap_percent": round(overlap_percent, 2),
        "mean_pixel_difference": round(mean_difference, 2),
        "changed_area_over_25_percent": round(changed_25, 2),
        "changed_area_over_50_percent": round(changed_50, 2),
        "reference_sha256": hashlib.sha256(reference_path.read_bytes()).hexdigest(),
        "caveat": (
            "La referencia confirma cambios visuales. Por sí sola no identifica la herramienta "
            "de edición ni demuestra suplantación de identidad."
        ),
    }
