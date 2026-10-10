"""Cover-noise initialisation for the MLX diffusion loop.

Mirrors the PyTorch ``generate_audio`` behaviour for ``cover_noise_strength``:
start denoising from a re-noised copy of the source latents instead of pure
noise, and skip the schedule steps above that noise level.
"""

from typing import Any, List, Tuple


def apply_cover_noise_init(
    t_schedule: List[float],
    noise: Any,
    src_latents: Any,
    cover_noise_strength: float,
) -> Tuple[Any, List[float]]:
    """Return the initial latent and the (possibly truncated) timestep schedule.

    Args:
        t_schedule: Descending timestep schedule (1.0 = pure noise).
        noise: Initial noise array, same shape as ``src_latents``.
        src_latents: Source latents to blend toward (``None`` disables blending).
        cover_noise_strength: 0.0 = pure noise (no-op), 1.0 = closest to source.

    Returns:
        ``(xt, schedule)`` where ``xt = t * noise + (1 - t) * src_latents`` at the
        schedule timestep nearest ``1 - cover_noise_strength``, and ``schedule``
        starts at that timestep. Unchanged ``(noise, t_schedule)`` when disabled.
    """
    if cover_noise_strength <= 0.0 or src_latents is None:
        return noise, t_schedule
    effective_noise_level = 1.0 - cover_noise_strength
    nearest_t = min(t_schedule, key=lambda t: abs(t - effective_noise_level))
    start_idx = t_schedule.index(nearest_t)
    xt = nearest_t * noise + (1.0 - nearest_t) * src_latents
    return xt, t_schedule[start_idx:]
