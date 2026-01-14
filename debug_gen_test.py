# -*- coding: utf-8 -*-
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.getcwd())

from backend.logic.generator import QuestionGenerator

def test_gen():
    gen = QuestionGenerator()
    
    # Test case 1: General node
    node_general = {
        "text": "이것은 테스트 문장입니다. 인공지능은 매우 중요합니다.",
        "roles": ["general"],
        "id": "1"
    }
    
    results = []
    
    results.append("Testing General Node (20 iterations):")
    # 히스토리를 초기화하지 않고 연속해서 생성하여 중복 방지 로직과 다양성을 테스트
    gen.reset_history() 
    for i in range(20):
        # 8개가 넘어가면 히스토리 리셋 효과로 다시 반복될 것임
        if i % 8 == 0:
             results.append(f"--- Cycle {i//8 + 1} ---")
        q = gen.generate(node_general)
        results.append(f"{i+1}. {q}")
        
    # Write to file
    with open("debug_output.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(results))
    
    # Print into console (limit output)
    print("\n" + "\n".join(results))
    print("\nResults also written to debug_output.txt")

if __name__ == "__main__":
    test_gen()
