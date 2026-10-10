#pragma once
#include "History.h"

struct GraphScale {
  bool valid = false;
  float lower = NAN, upper = NAN, step = NAN;
  uint32_t spanMs = 1000;
};

inline GraphScale graphScale(const TrendHistory& data, uint32_t now) {
  GraphScale result;
  float low = INFINITY, high = -INFINITY;
  uint32_t oldestAge = 0;
  for(unsigned i=0;i<data.size();++i) {
    const auto& sample=data.at(i); uint32_t age=now-sample.ms;
    if(age>600000) continue;
    if(age>oldestAge) oldestAge=age;
    const float readings[]={sample.pm25,sample.pm10};
    for(float v:readings) {
      if(!isfinite(v) || v<0) continue;
      if(v<low)low=v;
      if(v>high)high=v;
      result.valid=true;
    }
  }
  result.spanMs=oldestAge>1000?oldestAge:1000;
  if(!result.valid) return result;
  // Padding and rounded tick spacing are presentation settings, not sample data.
  float padding=fmaxf((high-low)*0.15f,fmaxf(high*0.015f,0.2f));
  float desiredLow=fmaxf(0,low-padding), desiredHigh=high+padding;
  float rawStep=(desiredHigh-desiredLow)/4;
  float magnitude=powf(10,floorf(log10f(rawStep)));
  float normalized=rawStep/magnitude;
  float factor=normalized<1.5f?1:normalized<3?2:normalized<7?5:10;
  result.step=factor*magnitude;
  result.lower=fmaxf(0,floorf(desiredLow/result.step)*result.step);
  result.upper=ceilf(desiredHigh/result.step)*result.step;
  return result;
}
