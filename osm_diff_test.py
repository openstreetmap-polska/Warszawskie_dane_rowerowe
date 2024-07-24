from osm_diff import h3LineLatLng


def testH3LineLatLng():
    assert h3LineLatLng((21, 52), (21.001, 52)) == {
        "8c1f53591c649ff",
        "8c1f53591d4a5ff",
        "8c1f53591d4a7ff",
        "8c1f53591d4b5ff",
        "8c1f53591d4b7ff",
    }
    assert h3LineLatLng((21, 52), (21.005, 52.001)) == {
        "8c1f535918803ff",
        "8c1f535918805ff",
        "8c1f535918807ff",
        "8c1f535918811ff",
        "8c1f53591881bff",
        "8c1f53591881dff",
        "8c1f535918829ff",
        "8c1f535918867ff",
        "8c1f535918943ff",
        "8c1f535918945ff",
        "8c1f535918947ff",
        "8c1f535918951ff",
        "8c1f53591895bff",
        "8c1f53591895dff",
        "8c1f535918969ff",
        "8c1f53591896dff",
        "8c1f535918aa7ff",
        "8c1f53591d4a3ff",
        "8c1f53591d4a5ff",
        "8c1f53591d4a7ff",
        "8c1f53591d4b1ff",
        "8c1f53591d4bbff",
        "8c1f53591d4bdff",
    }
