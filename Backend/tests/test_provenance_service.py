from app.services.provenance_service import _provenance_declarations


class _Reader:
    def __init__(self, manifests):
        self.manifests = manifests

    def get_manifest(self, label):
        return self.manifests[label]


def test_ai_declaration_is_collected_from_ingredient_chain():
    ingredient = {
        "label": "ingredient",
        "assertions": [
            {
                "label": "c2pa.actions.v2",
                "data": {
                    "actions": [
                        {
                            "action": "c2pa.created",
                            "digitalSourceType": (
                                "http://cv.iptc.org/newscodes/"
                                "digitalsourcetype/trainedAlgorithmicMedia"
                            ),
                            "description": "Created by Generative AI.",
                        }
                    ]
                },
            }
        ],
    }
    active = {
        "label": "active",
        "ingredients": [{"active_manifest": "ingredient"}],
    }

    result = _provenance_declarations(
        _Reader({"ingredient": ingredient}),
        active,
    )

    assert result["ai_created_declared"] is True
    assert result["ai_provenance_declared"] is True
    assert result["manifest_chain_depth"] == 2


def test_ordinary_edit_is_not_treated_as_ai_declaration():
    active = {
        "label": "active",
        "assertions": [
            {
                "label": "c2pa.actions.v2",
                "data": {"actions": [{"action": "c2pa.cropped"}]},
            }
        ],
    }

    result = _provenance_declarations(_Reader({}), active)

    assert result["ai_provenance_declared"] is False
