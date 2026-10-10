// TypeScript typings reflecting frozen Contract shapes for Member 3

// Contract 1: Sensor telemetry
export interface SensorReading {
  station_id: string;
  timestamp: string;
  pm25: number;
  pm10: number;
  temp: number;
  humidity: number;
  pressure: number;
}

// Contract 2: Source classifier attribution output
export interface AttributionOutput {
  prediction_set: string[];
  set_size: number;
  confidence: number;
  probabilities: Record<string, number>;
}

// Contract 3: AQI atmospheric forecast output
export interface ForecastOutput {
  horizon_h: number;
  point: number;
  interval: [number, number];
  ventilation_index: number;
}

// Contract 4: Solver vehicle dispatch routing output
export interface RouteStop {
  source_id: string;
  lat: number;
  lon: number;
  eta: string;
  action: string;
  roi: number;
}

export interface RoutePlan {
  route_id: string;
  stops: RouteStop[];
}
