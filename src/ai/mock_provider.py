"""Deterministic mock AI provider used for DEMO_MODE and unit tests.

No network calls. Produces plausible, structured fake output so the whole
pipeline (verification -> writing -> SEO -> fact-check) can be exercised
end-to-end without any external API keys.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional

from src.ai.base import AIProvider


class MockProvider(AIProvider):
    name = "mock"

    def generate(self, prompt: str, *, system: Optional[str] = None,
                 max_tokens: int = 2000, temperature: float = 0.4) -> str:
        # Very small heuristic "generator" so demo output differs per prompt.
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]
        return f"[mock-output-{digest}] {prompt[:60]}"

    def generate_json(self, prompt: str, *, system: Optional[str] = None,
                       max_tokens: int = 2000, temperature: float = 0.3) -> Dict[str, Any]:
        p = prompt.lower()
        if "verification_score" in prompt or "is_real_event" in prompt:
            return {
                "is_real_event": True,
                "is_recent": True,
                "is_newsworthy": True,
                "is_sensitive": False,
                "sufficient_source_support": True,
                "independent_source_count": 2,
                "confidence_notes": "mock verification pass",
                "verification_score": 82,
                "recommended_status": "good",
            }
        if "headline" in prompt and "body" in prompt and "editorial_angle" in prompt:
            digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:6]
            body_paragraphs = [
                "أفادت مصادر مطلعة بوقوع تطور جديد يتعلق بالحدث محل التغطية، حيث تشير المعلومات المتاحة إلى أهمية هذا التطور على الصعيدين المحلي والإقليمي.",
                "وبحسب المصادر المتاحة، فإن هذا التطور يأتي في سياق متابعة مستمرة لمجريات الأمور، مع تسليط الضوء على الجهات المعنية والأطراف ذات الصلة.",
                "من المتوقع أن يكون لهذا التطور تداعيات على القطاع المعني، وسط ترقب لمزيد من التفاصيل والتوضيحات من الجهات الرسمية خلال الساعات المقبلة.",
                "وتواصل عملية المتابعة الإعلامية رصد أي مستجدات إضافية تتعلق بهذا الملف، مع الالتزام بالتحقق من دقة المعلومات قبل نشرها.",
            ]
            return {
                "headline": f"تطورات جديدة في حدث رقم {digest}",
                "summary": "ملخص موجز للحدث يوضح أبرز النقاط الأساسية المرتبطة به.",
                "body": "\n\n".join(body_paragraphs),
                "entities": [],
                "editorial_angle": "تغطية تحريرية عامة",
            }
        if "seo_title" in prompt:
            digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]
            return {
                "seo_title": f"خبر عاجل - {digest}",
                "meta_description": "وصف تعريفي مختصر ودقيق للخبر دون مبالغة أو تضليل.",
                "slug": f"news-{digest}",
                "keywords": ["خبر", "تحديث", digest],
            }
        if "passed" in prompt or "corrected_body" in prompt:
            return {"passed": True, "issues": []}
        return {"mock": True, "prompt_excerpt": prompt[:80]}
