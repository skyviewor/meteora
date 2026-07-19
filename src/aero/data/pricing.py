"""Model pricing and TokenTracker for Aero.

All prices in CNY per 1K tokens.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ModelPrice:
    input_price: float
    cached_input_price: float
    output_price: float
    context_window: int


PRICING: dict[str, ModelPrice] = {
    # --- LLM ---
    # DeepSeek (USD → CNY at ~7.2 rate, per 1K tokens)
    "deepseek-v4-flash": ModelPrice(
        input_price=0.001008, cached_input_price=0.000020, output_price=0.002016,
        context_window=1_000_000,
    ),
    "deepseek-v4-pro": ModelPrice(
        input_price=0.003132, cached_input_price=0.000026, output_price=0.006264,
        context_window=1_000_000,
    ),
    "deepseek-chat": ModelPrice(
        input_price=0.001008, cached_input_price=0.000020, output_price=0.002016,
        context_window=1_000_000,
    ),
    "deepseek-reasoner": ModelPrice(
        input_price=0.001008, cached_input_price=0.000020, output_price=0.002016,
        context_window=1_000_000,
    ),
    # Kimi (CNY per 1K tokens)
    "kimi-k2.6": ModelPrice(
        input_price=0.0065, cached_input_price=0.0011, output_price=0.027,
        context_window=262_144,
    ),
    "kimi-k2.5": ModelPrice(
        input_price=0.004, cached_input_price=0.0007, output_price=0.021,
        context_window=262_144,
    ),
    "kimi-k2-thinking": ModelPrice(
        input_price=0.004, cached_input_price=0.0007, output_price=0.021,
        context_window=262_144,
    ),
    "kimi-k2-0905-preview": ModelPrice(
        input_price=0.004, cached_input_price=0.0007, output_price=0.021,
        context_window=262_144,
    ),
    "moonshot-v1-128k": ModelPrice(
        input_price=0.01, cached_input_price=0.01, output_price=0.03,
        context_window=131_072,
    ),
    "moonshot-v1-32k": ModelPrice(
        input_price=0.005, cached_input_price=0.005, output_price=0.02,
        context_window=32_768,
    ),
    # Qwen / Bailian (CNY per 1K tokens)
    "qwen3.7": ModelPrice(
        input_price=0.02, cached_input_price=0.02, output_price=0.06,
        context_window=131_072,
    ),
    "qwen-plus": ModelPrice(
        input_price=0.002, cached_input_price=0.002, output_price=0.006,
        context_window=131_072,
    ),
    "qwen-max": ModelPrice(
        input_price=0.02, cached_input_price=0.02, output_price=0.06,
        context_window=32_768,
    ),
    "qwen-turbo": ModelPrice(
        input_price=0.0005, cached_input_price=0.0005, output_price=0.0015,
        context_window=131_072,
    ),
    "qwen-long": ModelPrice(
        input_price=0.0005, cached_input_price=0.0005, output_price=0.0015,
        context_window=1_000_000,
    ),
    "qwen3-max": ModelPrice(
        input_price=0.008, cached_input_price=0.008, output_price=0.024,
        context_window=131_072,
    ),
    "qwen3-plus": ModelPrice(
        input_price=0.0035, cached_input_price=0.0035, output_price=0.0105,
        context_window=131_072,
    ),
    # OpenAI (USD → CNY, per 1K tokens; cache pricing from prompt caching docs)
    "gpt-4o": ModelPrice(
        input_price=0.018, cached_input_price=0.009, output_price=0.072,
        context_window=128_000,
    ),
    "gpt-4o-mini": ModelPrice(
        input_price=0.00108, cached_input_price=0.00054, output_price=0.00432,
        context_window=128_000,
    ),
    # --- Vision ---
    "qwen3-vl-plus": ModelPrice(
        input_price=0.003, cached_input_price=0.003, output_price=0.012,
        context_window=32_768,
    ),
    "qwen3-vl-flash": ModelPrice(
        input_price=0.0015, cached_input_price=0.0015, output_price=0.006,
        context_window=32_768,
    ),
    "qwen-vl-max": ModelPrice(
        input_price=0.003, cached_input_price=0.003, output_price=0.012,
        context_window=32_768,
    ),
    "qwen-vl-plus": ModelPrice(
        input_price=0.0015, cached_input_price=0.0015, output_price=0.006,
        context_window=32_768,
    ),
    "qwen3.5-flash": ModelPrice(
        input_price=0.0015, cached_input_price=0.0015, output_price=0.006,
        context_window=1_000_000,
    ),
    "qwen3.5-plus": ModelPrice(
        input_price=0.003, cached_input_price=0.003, output_price=0.012,
        context_window=1_000_000,
    ),
    "qwen3.6-flash": ModelPrice(
        input_price=0.0015, cached_input_price=0.0015, output_price=0.006,
        context_window=1_000_000,
    ),
    "qwen3.6-plus": ModelPrice(
        input_price=0.003, cached_input_price=0.003, output_price=0.012,
        context_window=1_000_000,
    ),
    "qwen3.7-plus": ModelPrice(
        input_price=0.003, cached_input_price=0.003, output_price=0.012,
        context_window=1_000_000,
    ),
}


# Context limits are independent from pricing so an unknown custom model never
# inherits a plausible-looking percentage from the fallback price.
CONTEXT_WINDOWS: dict[str, int] = {
    "deepseek-v4-flash": 1_000_000,
    "deepseek-v4-pro": 1_000_000,
    "qwen3.7-max": 1_000_000,
    "qwen3.7-plus": 1_000_000,
    "qwen3.6-plus": 1_000_000,
    "qwen3.6-flash": 1_000_000,
    "qwen3.5-plus": 1_000_000,
    "qwen3.5-flash": 1_000_000,
    "kimi-k3": 1_000_000,
    "kimi-k2.7-code": 262_144,
    "kimi-k2.6": 262_144,
    "kimi-k2.5": 262_144,
    "glm-5": 200_000,
    "glm-5.1-highspeed": 200_000,
    "glm-4.6v": 128_000,
    "glm-4.6v-flashx": 128_000,
    "minimax-m3": 1_000_000,
    "minimax-m2.7": 204_800,
    "minimax-m2.5": 204_800,
}


_DEFAULT_PRICE = ModelPrice(
    input_price=0.002, cached_input_price=0.002, output_price=0.008,
    context_window=128_000,
)


def get_price(model: str) -> ModelPrice:
    return PRICING.get(model, _DEFAULT_PRICE)


def context_window_for(model: str) -> int | None:
    return CONTEXT_WINDOWS.get(model.strip().lower())


@dataclass
class ModelUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0


def _sum_usage_attr(usages: dict[str, ModelUsage], attr: str) -> int:
    return sum(getattr(u, attr) for u in usages.values())


@dataclass
class TokenTracker:
    _llm_usage: dict[str, ModelUsage] = field(default_factory=dict)
    _vision_usage: dict[str, ModelUsage] = field(default_factory=dict)
    current_prompt_tokens: int = 0

    @property
    def prompt_tokens(self) -> int:
        return _sum_usage_attr(self._llm_usage, "prompt_tokens")

    @property
    def completion_tokens(self) -> int:
        return _sum_usage_attr(self._llm_usage, "completion_tokens")

    @property
    def cached_tokens(self) -> int:
        return _sum_usage_attr(self._llm_usage, "cached_tokens")

    @property
    def vision_prompt_tokens(self) -> int:
        return _sum_usage_attr(self._vision_usage, "prompt_tokens")

    @property
    def vision_completion_tokens(self) -> int:
        return _sum_usage_attr(self._vision_usage, "completion_tokens")

    @property
    def vision_cached_tokens(self) -> int:
        return _sum_usage_attr(self._vision_usage, "cached_tokens")

    @property
    def total_tokens(self) -> int:
        return (
            self.prompt_tokens
            + self.completion_tokens
            + self.vision_prompt_tokens
            + self.vision_completion_tokens
        )

    @property
    def llm_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def vision_tokens(self) -> int:
        return self.vision_prompt_tokens + self.vision_completion_tokens

    def add_llm(self, usage: dict | None, model: str) -> None:
        if not usage:
            return
        current_prompt = usage.get("prompt_tokens", 0)
        completion = usage.get("completion_tokens", 0)
        details = usage.get("prompt_tokens_details")
        cached = details.get("cached_tokens", 0) if isinstance(details, dict) else 0

        entry = self._llm_usage.setdefault(model, ModelUsage())
        entry.prompt_tokens += current_prompt
        entry.completion_tokens += completion
        entry.cached_tokens += cached
        self.current_prompt_tokens = current_prompt

    def add_vision(self, usage: dict | None, model: str) -> None:
        if not usage:
            return
        prompt = usage.get("prompt_tokens", 0)
        completion = usage.get("completion_tokens", 0)
        details = usage.get("prompt_tokens_details")
        cached = details.get("cached_tokens", 0) if isinstance(details, dict) else 0

        entry = self._vision_usage.setdefault(model, ModelUsage())
        entry.prompt_tokens += prompt
        entry.completion_tokens += completion
        entry.cached_tokens += cached

    def total_cost(self) -> float:
        cost = 0.0
        for model, u in self._llm_usage.items():
            price = get_price(model)
            non_cached = u.prompt_tokens - u.cached_tokens
            cost += (
                non_cached * price.input_price
                + u.cached_tokens * price.cached_input_price
                + u.completion_tokens * price.output_price
            ) / 1000
        for model, u in self._vision_usage.items():
            price = get_price(model)
            non_cached = u.prompt_tokens - u.cached_tokens
            cost += (
                non_cached * price.input_price
                + u.cached_tokens * price.cached_input_price
                + u.completion_tokens * price.output_price
            ) / 1000
        return cost

    def cache_ratio(self) -> float:
        if self.prompt_tokens == 0:
            return 0
        return self.cached_tokens / self.prompt_tokens

    def to_dict(self) -> dict:
        return {
            "llm_usage": {
                model: {
                    "prompt_tokens": u.prompt_tokens,
                    "completion_tokens": u.completion_tokens,
                    "cached_tokens": u.cached_tokens,
                }
                for model, u in self._llm_usage.items()
            },
            "vision_usage": {
                model: {
                    "prompt_tokens": u.prompt_tokens,
                    "completion_tokens": u.completion_tokens,
                    "cached_tokens": u.cached_tokens,
                }
                for model, u in self._vision_usage.items()
            },
            "current_prompt_tokens": self.current_prompt_tokens,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TokenTracker":
        llm_usage = {}
        for model, u in d.get("llm_usage", {}).items():
            llm_usage[model] = ModelUsage(
                prompt_tokens=u.get("prompt_tokens", 0),
                completion_tokens=u.get("completion_tokens", 0),
                cached_tokens=u.get("cached_tokens", 0),
            )
        vision_usage = {}
        for model, u in d.get("vision_usage", {}).items():
            vision_usage[model] = ModelUsage(
                prompt_tokens=u.get("prompt_tokens", 0),
                completion_tokens=u.get("completion_tokens", 0),
                cached_tokens=u.get("cached_tokens", 0),
            )
        return cls(
            _llm_usage=llm_usage,
            _vision_usage=vision_usage,
            current_prompt_tokens=d.get("current_prompt_tokens", 0),
        )

    def copy(self) -> "TokenTracker":
        return TokenTracker(
            _llm_usage={
                model: ModelUsage(
                    prompt_tokens=u.prompt_tokens,
                    completion_tokens=u.completion_tokens,
                    cached_tokens=u.cached_tokens,
                )
                for model, u in self._llm_usage.items()
            },
            _vision_usage={
                model: ModelUsage(
                    prompt_tokens=u.prompt_tokens,
                    completion_tokens=u.completion_tokens,
                    cached_tokens=u.cached_tokens,
                )
                for model, u in self._vision_usage.items()
            },
            current_prompt_tokens=self.current_prompt_tokens,
        )


def format_token_count(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def format_cost(n: float) -> str:
    return f"¥{n:.2f}"
