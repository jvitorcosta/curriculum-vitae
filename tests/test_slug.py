from cv.slug import filename_part, slugify


def test_slugify_folds_accents_and_punctuation():
    assert slugify("Comgás") == "comgas"
    assert slugify("Wayne Technology | Nearshore Software Development") == "wayne-technology-nearshore-software"
    assert slugify("Engenheiro de IA Sênior") == "engenheiro-de-ia-senior"


def test_filename_part():
    assert filename_part("Acme Labs") == "Acme_Labs"
    assert filename_part("Vandelay Import Export") == "Vandelay_Import_Export"
    assert filename_part("Comgás") == "Comgas"
