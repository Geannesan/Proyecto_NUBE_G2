import argparse
import json
from pathlib import Path

from PIL import Image

from app.detector.audio_detector import analyze_audio
from app.detector.image_ai_detector import analyze_image_ai
from app.detector.image_deepfake_detector import (
    analyze_image_deepfake,
)
from app.detector.video_detector import analyze_video


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Prueba manual de los detectores "
            "de DeepFakeShield."
        )
    )

    parser.add_argument(
        "media_type",
        choices=["image", "audio", "video"],
    )

    parser.add_argument(
        "file",
        type=Path,
    )

    parser.add_argument(
        "--detector",
        choices=["ai", "deepfake"],
        default="ai",
    )

    args = parser.parse_args()

    if not args.file.exists():
        raise FileNotFoundError(
            f"No existe: {args.file}"
        )

    if args.media_type == "image":
        with Image.open(args.file) as image:
            if args.detector == "ai":
                result = analyze_image_ai(image)
            else:
                result = analyze_image_deepfake(
                    image
                )

    elif args.media_type == "audio":
        result = analyze_audio(args.file)

    else:
        result = analyze_video(
            args.file,
            detector_type=args.detector,
        )

    print(
        json.dumps(
            result.as_dict(),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
