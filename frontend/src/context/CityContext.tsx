'use client';
import React, { createContext, useContext, useState, useEffect, useMemo } from 'react';
import { Station, CityId, District, AqiStandard } from '@/types';
import { computeDelhiDistricts } from '@/data/delhiDistricts';
import { computeHyderabadDistricts, computeGuwahatiDistricts, computeBengaluruDistricts } from '@/data/otherDistricts';
import { apiUrl } from '@/utils/api';

interface CityContextType {
  activeCity: CityId;
  setActiveCity: (city: CityId) => void;
  cityData: any;
  liveData: any;
  userCoords: { lat: number; lon: number } | null;
  liveLoading: boolean;
  stations: Station[];
  districts: District[];
  aqiStandard: AqiStandard;
  setAqiStandard: (std: AqiStandard) => void;
}


const CityContext = createContext<CityContextType | null>(null);

export function useCityContext() {
  const ctx = useContext(CityContext);
  if (!ctx) throw new Error('useCityContext must be used within CityProvider');
  return ctx;
}

export function CityProvider({ children }: { children: React.ReactNode }) {
  const [activeCity, setActiveCity] = useState<CityId>('Hyderabad');
  const [aqiStandard, setAqiStandard] = useState<AqiStandard>('IN_NAQI');
  const [cityData, setCityData] = useState<any>(null);
  const [liveData, setLiveData] = useState<any>(null);
  const [userCoords, setUserCoords] = useState<{ lat: number; lon: number } | null>(null);
  const [liveLoading, setLiveLoading] = useState(false);

  const cityCacheRef = React.useRef<Record<string, any>>({});


  // Geolocate for "My Location"
  useEffect(() => {
    if (activeCity === 'My Location') {
      if (navigator.geolocation) {
        setLiveLoading(true);
        navigator.geolocation.getCurrentPosition(
          (pos) => setUserCoords({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
          () => {
            alert('Failed to get location. Defaulting to Hyderabad.');
            setActiveCity('Hyderabad');
            setLiveLoading(false);
          }
        );
      } else {
        alert('Geolocation not supported. Defaulting to Hyderabad.');
        setActiveCity('Hyderabad');
      }
    }
  }, [activeCity]);

  // Fetch live GPS data
  useEffect(() => {
    if (activeCity === 'My Location' && userCoords) {
      setLiveLoading(true);
      fetch(apiUrl(`/api/live?lat=${userCoords.lat}&lon=${userCoords.lon}`))
        .then((r) => r.json())
        .then((data) => { setLiveData(data); setLiveLoading(false); })
        .catch(() => setLiveLoading(false));
    }
  }, [activeCity, userCoords]);

  // Fetch city data with instant cache-first and background revalidation
  useEffect(() => {
    if (activeCity !== 'My Location') {
      let isMounted = true;
      if (cityCacheRef.current[activeCity]) {
        setCityData(cityCacheRef.current[activeCity]);
        setLiveLoading(false);
      } else {
        setLiveLoading(true);
      }
      
      const fetchCity = (retryCount = 0) => {
        fetch(apiUrl(`/api/city-data?city=${activeCity}`))
          .then((r) => {
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            return r.json();
          })
          .then((data) => {
            if (isMounted) {
              cityCacheRef.current[activeCity] = data;
              setCityData(data);
              setLiveLoading(false);
            }
          })
          .catch((err) => {
            if (retryCount < 2) {
              setTimeout(() => {
                if (isMounted) fetchCity(retryCount + 1);
              }, 1000);
            } else if (isMounted) {
              setLiveLoading(false);
            }
          });
      };

      fetchCity();
      return () => { isMounted = false; };
    }
  }, [activeCity]);

  // Derive stations from raw data
  const stations: Station[] = useMemo(() => {
    if (activeCity === 'My Location' && liveData) {
      return [{
        id: 'USER_GPS',
        name: 'My Location',
        lat: userCoords?.lat ?? 0,
        lon: userCoords?.lon ?? 0,
        pm25: liveData.reading.pm25,
        pm10: liveData.reading.pm10,
        no2: 40, so2: 12, co: 1.5, o3: 30,
        aqi: liveData.live_aqi,
        source: 'deployed',
        status: 'online',
      }];
    }
    return cityData?.stations ?? [];
  }, [activeCity, liveData, cityData, userCoords]);

  // Compute districts for spatial analytics and telemetry
  const districts = useMemo(() => {
    if (activeCity === 'Delhi') return computeDelhiDistricts(stations, aqiStandard);
    if (activeCity === 'Hyderabad') return computeHyderabadDistricts(stations, aqiStandard);
    if (activeCity === 'Guwahati') return computeGuwahatiDistricts(stations, aqiStandard);
    if (activeCity === 'Bengaluru') return computeBengaluruDistricts(stations, aqiStandard);
    return [];
  }, [activeCity, stations, aqiStandard]);

  return (
    <CityContext.Provider value={{
      activeCity, setActiveCity,
      cityData, liveData, userCoords, liveLoading,
      stations, districts,
      aqiStandard, setAqiStandard,
    }}>
      {children}
    </CityContext.Provider>
  );
}

