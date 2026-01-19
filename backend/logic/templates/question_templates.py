from __future__ import annotations
from typing import Dict, List

QUESTION_TEMPLATES: Dict[str, List[Dict[str, str]]] = {
            "definition": [
                {"id": "definition_01", "text": "'{snippet}'에서 '{entity}'는 어떤 의미로 정의되나요?"},
                {"id": "definition_02", "text": "본문에서 '{entity}'의 정의를 한 문장으로 정리해볼까요?"},
            ],
            "claim": [
                # [QAR: Think and Search] 주장 파악
                {"id": "claim_01", "text": "'{snippet}'에서 필자가 강조하고자 하는 핵심 주장은 무엇인가요?"},
                
                # [Socratic] 전제 확인
                {"id": "claim_02", "text": "그 해석은 '{snippet}' 내용이 반드시 참이라는 가정이 필요한데, 그 근거는 무엇인가요?"},
                
                # [Toulmin] 영장 탐색
                {"id": "claim_03", "text": "제시된 근거에서 이 주장('{snippet}')으로 나아가기 위해, 필자는 어떤 논리적 연결 고리를 사용하고 있나요?"},
                
                # [Toulmin] 반박 고려
                {"id": "claim_04", "text": "어떤 상황에서 '{snippet}'(이)라는 주장이 성립하지 않을 수 있을까요?"},
                
                # [Review] 요약하기 (Reciprocal Teaching)
                {"id": "claim_05", "text": "지금까지의 논리를 한 문장으로 압축해 볼까요?"},

                # [Bloom: Analyze] 의도 파악
                {"id": "claim_06", "text": "글쓴이가 '{snippet}'라고 주장하는 이면에 깔린 궁극적인 의도는 무엇일까요?"},

                # [Bloom: Application] 적용하기
                {"id": "claim_07", "text": "이 주장('{snippet}')을 우리 현실 문제에 적용한다면 어떤 사례를 들 수 있을까요?"},
            ],
            "evidence": [
                # [QAR: Right There] 명시적 정보 확인
                {"id": "evidence_01", "text": "본문에서 '{entity}'(은)는 무엇이라고 명시되어 있나요?"},
                
                # [Socratic] 증거 탐구
                {"id": "evidence_02", "text": "본문의 정확히 어느 문장이 '{snippet}' 내용을 뒷받침하나요?"},
                
                # [Toulmin] 보강 요구
                {"id": "evidence_03", "text": "'{snippet}'만으로 주장을 뒷받침하기에 충분한가요? 아니면 추가 근거가 더 필요할까요?"},
                
                # [Bloom: Evaluate] 근거 평가
                {"id": "evidence_04", "text": "저자가 제시한 '{entity}' 관련 근거가 주장을 뒷받침하기에 충분히 객관적인가요?"},

                # [Critical Thinking] 정보 공백 확인
                {"id": "evidence_05", "text": "이 근거('{snippet}') 말고도 주장을 강화하기 위해 더 필요한 정보가 있다면 무엇일까요?"},

                # [Socratic] 대안적 해석
                {"id": "evidence_06", "text": "혹시 이 근거('{snippet}')를 다른 방식으로 해석할 여지는 없을까요?"},
            ],
            "cause": [
                # [QAR: Think and Search] 원인 분석
                {"id": "cause_01", "text": "본문의 여러 부분을 종합해 볼 때, '{snippet}' 현상이 발생한 복합적인 원인은 무엇인가요?"},
                
                # [Thinking Routine] See-Think-Wonder
                {"id": "cause_02", "text": "'{entity}' 원인과 관련하여, 텍스트에서 발견한 사실(See)과 당신의 해석(Think)을 구분해서 설명해 줄 수 있나요?"},
                
                # [Bloom: Analyze] 인과관계 분석
                {"id": "cause_03", "text": "이러한 배경이 결과적으로 '{snippet}'에 어떤 영향을 미쳤는지 논리적으로 연결해 볼까요?"},

                # [Systems Thinking] 근본 원인 탐색
                {"id": "cause_04", "text": "직접적인 원인 외에, '{snippet}' 현상을 초래한 근본적인(사회적/구조적) 배경은 무엇일까요?"},

                # [Logic Check] 인과관계 검증
                {"id": "cause_05", "text": "이 원인('{snippet}')과 결과 사이의 연결 고리가 필연적인가요, 아니면 우연적인 요소도 있나요?"},
            ],
            "result": [
                # [Socratic] 결과 및 함축
                {"id": "result_01", "text": "사용자님의 해석대로라면, '{snippet}' 이후에 어떤 내용이 이어져야 논리적으로 타당할까요?"},
                
                # [Reciprocal Teaching] 예측하기
                {"id": "result_02", "text": "'{entity}'(으)로 인한 결과를 바탕으로, 저자가 다음 단락에서 어떤 논리를 펴나갈 것이라 예상하나요?"},
                
                # [Bloom: Create] 가설 및 적용
                {"id": "result_03", "text": "만약 이 결과('{snippet}')가 발생하지 않았다면, 상황은 어떻게 달라졌을까요?"},
                
                # [Thinking Routine] See-Think-Wonder (Wonder focus)
                {"id": "result_04", "text": "이 결과와 관련하여 더 궁금한 점(Wonder)은 무엇인가요?"},

                # [Bloom: Evaluate] 파급 효과 평가
                {"id": "result_05", "text": "이 결과('{snippet}')가 긍정적인 측면만 있을까요? 혹시 부정적인 부작용은 없을까요?"},

                # [Interpretation] 주제 연결
                {"id": "result_06", "text": "이 결과('{snippet}')를 통해 저자가 최종적으로 전달하려는 메시지는 무엇일까요?"},
            ],
            "contrast": [
                # [Socratic] 관점 전환
                {"id": "contrast_01", "text": "만약 저자와 반대되는 입장이라면 '{snippet}' 내용을 어떻게 반박할 수 있을까요?"},
                
                # [Bloom: Analyze] 대조 분석
                {"id": "contrast_02", "text": "필자가 '{entity}'을(를) 대비시키며 강조하고자 하는 논리적 차이점은 무엇인가요?"},
                
                # [Six Hats] 검은 모자 (부정/비판)
                {"id": "contrast_03", "text": "이 대조 논리에서 놓치고 있는 예외 상황이나 허점은 없을까요?"},
                
                # [Thinking Routine] Compare-Contrast
                {"id": "contrast_04", "text": "'{entity}'와(과) 비교할 때 가장 두드러지는 차이점은 무엇인가요?"},

                # [Synthesis] 통합적 사고
                {"id": "contrast_05", "text": "두 입장('{entity}') 사이에서 중재안을 찾는다면 어떤 결론을 내릴 수 있을까요?"},

                # [Value Assessment] 가치 평가
                {"id": "contrast_06", "text": "이 대조('{snippet}')를 통해 필자가 부각하고 싶은 핵심 가치는 무엇인가요?"},
            ],
            "report": [
                {"id": "report_01", "text": "'{snippet}'라는 발언/전달이 나오는데, 이게 글의 논지에서 어떤 역할을 하나요?"},
                {"id": "report_02", "text": "이 발언('{snippet}')이 글 전체 주장과 어떻게 연결되나요?"},
            ],
            "general": [
                # [QAR: Author and Me] 저자와 내 생각
                {"id": "general_01", "text": "저자가 말한 '{snippet}' 개념을 당신의 실제 경험에 비추어 설명해 본다면?"},
                
                # [QAR: On My Own] 내 힘으로
                {"id": "general_02", "text": "이 글의 주제와 관련하여, 당신이라면 '{entity}' 문제에 대해 어떤 해결책을 제시하겠나요?"},
                
                # [Thinking Routine] See-Think-Wonder (Opening)
                {"id": "general_03", "text": "'{snippet}' 문장에서 무엇이 보이고(See), 그것이 무엇을 의미한다고 생각하시나요(Think)?"},
                
                # [Reciprocal Teaching] 명료화하기
                {"id": "general_04", "text": "이 문맥에서 '{entity}'(이)라는 단어는 흔히 아는 뜻과 다르게 쓰인 것 같은데, 어떻게 정의할 수 있을까요?"},
                
                # [Bloom: Analyze] 구조 파악
                {"id": "general_05", "text": "이 문단이 전체 주장 중 어떤 논리적 단계를 담당하고 있나요?"},

                # [Socratic] 다각도 분석 (Contrast 유도)
                {"id": "general_06", "text": "만약 '{snippet}' 내용에 반대하는 사람이 있다면, 어떤 근거를 들 수 있을까요?"},

                # [Bloom: Apply] 적용 및 예측 (Result 유도)
                {"id": "general_07", "text": "'{snippet}' 상황이 우리 사회(혹은 주변)에 직접 적용된다면 어떤 변화가 생길까요?"},

                # [Critical Thinking] 심층 탐구 (Cause 유도)
                {"id": "general_08", "text": "필자가 굳이 '{snippet}'(이)라고 표현한 의도나 숨겨진 의미는 무엇일까요?"},
            ],
        }