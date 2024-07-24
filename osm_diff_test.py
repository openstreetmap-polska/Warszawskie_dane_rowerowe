from osm_diff import h3LineLatLng


def testH3LineLatLng():
    assert h3LineLatLng((21, 52), (21.001, 52)) == {
        "8b1f53591d4afff",
        "8b1f53591d4bfff",
    }
    assert h3LineLatLng((21, 52), (21.005, 52.001)) == {
        '8b1f53591880fff',
        '8b1f53591881fff',
        '8b1f53591882fff',
        '8b1f53591894fff',
        '8b1f53591895fff',
        '8b1f53591896fff',
        '8b1f535918aafff',
        '8b1f53591d4afff',
        '8b1f53591d4bfff',
    }

