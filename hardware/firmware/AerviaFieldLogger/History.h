#pragma once
#include <stdint.h>
#include <math.h>

struct TrendSample { uint32_t ms; float pm25, pm10; };
class TrendHistory {
 public:
  static constexpr unsigned capacity = 600;
  void add(uint32_t ms, float pm25, float pm10) {
    samples[head] = {ms, pm25, pm10};
    head = (head + 1) % capacity;
    if (used < capacity) ++used;
  }
  unsigned size() const { return used; }
  const TrendSample& at(unsigned chronologicalIndex) const {
    return samples[(head + capacity - used + chronologicalIndex) % capacity];
  }
  bool stats(uint32_t now, float& low, float& mean, float& high) const {
    unsigned count = 0; float sum = 0;
    low = INFINITY; high = -INFINITY;
    for (unsigned i = 0; i < used; ++i) {
      const auto& s = at(i);
      if (uint32_t(now - s.ms) > 600000 || !isfinite(s.pm25)) continue;
      if (s.pm25 < low) low = s.pm25;
      if (s.pm25 > high) high = s.pm25;
      sum += s.pm25; ++count;
    }
    mean = count ? sum / count : NAN;
    return count > 0;
  }
  // Compare consecutive 30-second windows; require coverage in both windows.
  bool delta(uint32_t now, float& change) const {
    float recent = 0, previous = 0; unsigned nr = 0, np = 0;
    for (unsigned i = 0; i < used; ++i) {
      const auto& s = at(i); const uint32_t age = now - s.ms;
      if (!isfinite(s.pm25)) continue;
      if (age < 30000) { recent += s.pm25; ++nr; }
      else if (age < 60000) { previous += s.pm25; ++np; }
    }
    if (nr < 20 || np < 20) { change = NAN; return false; }
    change = recent / nr - previous / np; return true;
  }
 private:
  TrendSample samples[capacity] = {};
  unsigned head = 0, used = 0;
};

// Active-low, normally-open button. A held button emits Home once and no Next.
class PageButton {
 public:
  enum Event { None, Next, Home };
  Event update(bool pressed, uint32_t now) {
    if (pressed != raw) { raw = pressed; changedAt = now; }
    Event event = None;
    if (raw != stable && uint32_t(now - changedAt) >= 35) {
      stable = raw;
      if (stable) { pressedAt = now; held = false; }
      else if (!held) event = Next;
    }
    if (stable && !held && uint32_t(now - pressedAt) >= 900) {
      held = true; event = Home;
    }
    return event;
  }
 private:
  bool raw = false, stable = false, held = false;
  uint32_t changedAt = 0, pressedAt = 0;
};
