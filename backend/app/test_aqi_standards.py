from app.aqi_standards import (
    calc_cpcb_sub_index,
    calc_india_naqi,
    get_cpcb_category,
    calc_epa_sub_index,
    calc_us_epa_aqi,
    get_epa_category,
)

def test_india_naqi_pm25():
    # 25 ug/m3 -> Good (0-50)
    sub = calc_cpcb_sub_index("pm25", 25.0)
    assert 0 <= sub <= 50

    # 45 ug/m3 -> Satisfactory (51-100)
    sub = calc_cpcb_sub_index("pm25", 45.0)
    assert 51 <= sub <= 100

    # 75 ug/m3 -> Moderate (101-200)
    sub = calc_cpcb_sub_index("pm25", 75.0)
    assert 101 <= sub <= 200

    # 110 ug/m3 -> Poor (201-300)
    sub = calc_cpcb_sub_index("pm25", 110.0)
    assert 201 <= sub <= 300

    # 200 ug/m3 -> Very Poor (301-400)
    sub = calc_cpcb_sub_index("pm25", 200.0)
    assert 301 <= sub <= 400

    # 300 ug/m3 -> Severe (401-500)
    sub = calc_cpcb_sub_index("pm25", 300.0)
    assert 401 <= sub <= 500

def test_overall_india_naqi():
    # PM2.5 = 75 (Moderate: ~150), PM10 = 40 (Good: ~40), NO2 = 20 (Good: ~25)
    aqi, primary, subs = calc_india_naqi(pm25=75.0, pm10=40.0, no2=20.0)
    assert primary == "PM2.5"
    assert 140 <= aqi <= 160
    cat = get_cpcb_category(aqi)
    assert cat["category"] == "Moderate"

def test_us_epa_aqi():
    # PM2.5 = 10 -> Good (0-50)
    sub = calc_epa_sub_index("pm25", 10.0)
    assert 0 <= sub <= 50

    # PM2.5 = 25 -> Moderate (51-100)
    sub = calc_epa_sub_index("pm25", 25.0)
    assert 51 <= sub <= 100

    # PM2.5 = 45 -> USG (101-150)
    sub = calc_epa_sub_index("pm25", 45.0)
    assert 101 <= sub <= 150

    aqi, primary, subs = calc_us_epa_aqi(pm25=45.0, pm10=30.0)
    assert primary == "PM2.5"
    assert 101 <= aqi <= 150
    cat = get_epa_category(aqi)
    assert cat["category"] == "Unhealthy for Sensitive Groups"


def test_co_unit_normalization():
    # 62 ug/m3 of CO -> 0.062 mg/m3 -> sub-index should be around 3.1 (Good)
    sub_cpcb = calc_cpcb_sub_index("co", 62.0)
    assert 0 <= sub_cpcb <= 10

    # 1.5 mg/m3 of CO -> Satisfactory (~75)
    sub_cpcb_direct_mg = calc_cpcb_sub_index("co", 1.5)
    assert 51 <= sub_cpcb_direct_mg <= 100

    # US EPA: 62 ug/m3 -> ~0.054 ppm -> sub-index < 5
    sub_epa = calc_epa_sub_index("co", 62.0)
    assert 0 <= sub_epa <= 10

if __name__ == "__main__":
    test_india_naqi_pm25()
    print("test_india_naqi_pm25 passed")
    test_overall_india_naqi()
    print("test_overall_india_naqi passed")
    test_us_epa_aqi()
    print("test_us_epa_aqi passed")
    test_co_unit_normalization()
    print("test_co_unit_normalization passed")
    print("ALL TESTS PASSED SUCCESSFULLY!")
