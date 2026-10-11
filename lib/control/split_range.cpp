#include "split_range.h"

SplitRange::SplitRange(float fan_min, float on_threshold, float off_threshold, float fan_scale)
    : fan_min_(fan_min), on_th_(on_threshold), off_th_(off_threshold), fan_scale_(fan_scale) {}

void SplitRange::update(float u, float& lamps, float& fan) {
  if (u > 1.0f) u = 1.0f;
  if (u < -1.0f) u = -1.0f;

  lamps = u > 0.0f ? u : 0.0f;

  float demand = u < 0.0f ? -u * fan_scale_ : 0.0f;
  if (demand > 1.0f) demand = 1.0f;
  if (!fan_on_ && demand > on_th_) fan_on_ = true;
  else if (fan_on_ && demand < off_th_) fan_on_ = false;

  fan = fan_on_ ? fan_min_ + (1.0f - fan_min_) * demand : 0.0f;
  if (fan > 1.0f) fan = 1.0f;
}
