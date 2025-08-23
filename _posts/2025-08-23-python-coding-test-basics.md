---
layout: post
title: "파이썬 코딩테스트 기초 문제 완전 정복"
date: 2025-08-23 10:00:00 +0900
categories: [Python, Algorithm, CodingTest]
tags: [python, algorithm, coding-test, programming, interview, problem-solving]
excerpt: "파이썬으로 풀어보는 코딩테스트 기초 문제들과 해결 전략을 단계별로 알아봅시다. 초보자도 쉽게 따라할 수 있는 실전 문제 해결 가이드입니다."
---

## 개요

코딩테스트는 개발자 취업의 필수 관문이 되었습니다. 특히 파이썬은 간결한 문법과 풍부한 라이브러리 덕분에 코딩테스트에서 인기 있는 언어입니다. 이번 포스트에서는 **파이썬 코딩테스트 기초 문제들**을 유형별로 분류하여 단계적으로 해결해보겠습니다.

## 코딩테스트 준비 팁

### 1. 파이썬 기본 세팅

```python
# 기본 입력 처리
import sys
input = sys.stdin.readline  # 빠른 입력 처리

# 자주 사용하는 라이브러리
from collections import deque, defaultdict, Counter
from itertools import combinations, permutations
import heapq
import math
```

### 2. 시간복잡도 체크리스트

- **O(1)**: 해시맵 접근, 배열 인덱스 접근
- **O(log N)**: 이진 탐색, 힙 연산
- **O(N)**: 선형 탐색, 배열 순회
- **O(N log N)**: 정렬, 분할정복
- **O(N²)**: 이중 반복문, 버블정렬

### 3. 공간복잡도 고려사항

```python
# 메모리 제한 확인 (보통 128MB ~ 512MB)
# 대략적인 계산: 1MB = 1,000,000 바이트 ≈ 250,000개의 정수
```

## 문제 유형별 해결 전략

## 1. 문자열 처리

### 문제 1: 회문(Palindrome) 판별

**문제**: 주어진 문자열이 회문인지 판별하세요.

```python
def is_palindrome_basic(s):
    """기본적인 회문 판별"""
    # 대소문자 구분 없이, 알파벳과 숫자만 고려
    cleaned = ''.join(char.lower() for char in s if char.isalnum())
    return cleaned == cleaned[::-1]

def is_palindrome_optimized(s):
    """최적화된 회문 판별 (투 포인터)"""
    left, right = 0, len(s) - 1
    
    while left < right:
        # 알파벳/숫자가 아닌 문자 건너뛰기
        while left < right and not s[left].isalnum():
            left += 1
        while left < right and not s[right].isalnum():
            right -= 1
        
        # 대소문자 무시하고 비교
        if s[left].lower() != s[right].lower():
            return False
        
        left += 1
        right -= 1
    
    return True

# 테스트
test_cases = [
    "A man, a plan, a canal: Panama",  # True
    "race a car",  # False
    "Was it a car or a cat I saw?",  # True
]

for test in test_cases:
    print(f"'{test}' -> {is_palindrome_optimized(test)}")
```

### 문제 2: 문자열 압축

**문제**: 연속된 같은 문자를 개수와 함께 압축하세요.

```python
def compress_string(s):
    """문자열 압축 (Run-Length Encoding)"""
    if not s:
        return ""
    
    result = []
    current_char = s[0]
    count = 1
    
    for i in range(1, len(s)):
        if s[i] == current_char:
            count += 1
        else:
            # 이전 문자와 개수 추가
            result.append(current_char)
            if count > 1:
                result.append(str(count))
            
            # 새로운 문자로 초기화
            current_char = s[i]
            count = 1
    
    # 마지막 문자 처리
    result.append(current_char)
    if count > 1:
        result.append(str(count))
    
    compressed = ''.join(result)
    
    # 압축된 길이가 원래보다 크면 원본 반환
    return compressed if len(compressed) < len(s) else s

# 테스트
test_strings = ["aabcccccaaa", "abcdef", "aabbcc"]
for s in test_strings:
    print(f"'{s}' -> '{compress_string(s)}'")
```

## 2. 배열/리스트 문제

### 문제 3: 두 수의 합

**문제**: 배열에서 두 수를 더해 target이 되는 인덱스 쌍을 찾으세요.

```python
def two_sum_brute_force(nums, target):
    """무차별 대입법 - O(N²)"""
    n = len(nums)
    for i in range(n):
        for j in range(i + 1, n):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []

def two_sum_hash(nums, target):
    """해시맵 활용 - O(N)"""
    num_to_index = {}
    
    for i, num in enumerate(nums):
        complement = target - num
        if complement in num_to_index:
            return [num_to_index[complement], i]
        num_to_index[num] = i
    
    return []

# 테스트
nums = [2, 7, 11, 15]
target = 9
print(f"Input: {nums}, Target: {target}")
print(f"Result: {two_sum_hash(nums, target)}")  # [0, 1]
```

### 문제 4: 배열 회전

**문제**: 배열을 오른쪽으로 k번 회전시키세요.

```python
def rotate_array_extra_space(nums, k):
    """추가 공간 사용 - O(N) 공간"""
    n = len(nums)
    k = k % n  # k가 배열 길이보다 클 수 있음
    return nums[-k:] + nums[:-k]

def rotate_array_inplace(nums, k):
    """제자리에서 회전 - O(1) 공간"""
    def reverse(arr, start, end):
        while start < end:
            arr[start], arr[end] = arr[end], arr[start]
            start += 1
            end -= 1
    
    n = len(nums)
    k = k % n
    
    # 전체 배열 뒤집기
    reverse(nums, 0, n - 1)
    # 첫 k개 원소 뒤집기
    reverse(nums, 0, k - 1)
    # 나머지 원소 뒤집기
    reverse(nums, k, n - 1)
    
    return nums

# 테스트
nums = [1, 2, 3, 4, 5, 6, 7]
k = 3
print(f"Original: {nums}")
print(f"Rotated by {k}: {rotate_array_inplace(nums.copy(), k)}")
```

## 3. 정렬과 탐색

### 문제 5: 이진 탐색

**문제**: 정렬된 배열에서 target의 위치를 찾으세요.

```python
def binary_search_iterative(nums, target):
    """반복문으로 이진 탐색"""
    left, right = 0, len(nums) - 1
    
    while left <= right:
        mid = (left + right) // 2
        
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    
    return -1

def binary_search_recursive(nums, target, left=0, right=None):
    """재귀로 이진 탐색"""
    if right is None:
        right = len(nums) - 1
    
    if left > right:
        return -1
    
    mid = (left + right) // 2
    
    if nums[mid] == target:
        return mid
    elif nums[mid] < target:
        return binary_search_recursive(nums, target, mid + 1, right)
    else:
        return binary_search_recursive(nums, target, left, mid - 1)

# 테스트
nums = [1, 3, 5, 7, 9, 11, 13, 15]
target = 7
print(f"Array: {nums}")
print(f"Target {target} found at index: {binary_search_iterative(nums, target)}")
```

### 문제 6: 합병 정렬

**문제**: 합병 정렬을 구현하세요.

```python
def merge_sort(arr):
    """합병 정렬 구현"""
    if len(arr) <= 1:
        return arr
    
    # 분할
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    
    # 정복 (합병)
    return merge(left, right)

def merge(left, right):
    """두 정렬된 배열 합병"""
    result = []
    i = j = 0
    
    # 두 배열을 비교하며 합병
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    
    # 남은 원소들 추가
    result.extend(left[i:])
    result.extend(right[j:])
    
    return result

# 테스트
arr = [64, 34, 25, 12, 22, 11, 90]
print(f"Original: {arr}")
print(f"Sorted: {merge_sort(arr)}")
```

## 4. 스택과 큐

### 문제 7: 괄호 검사

**문제**: 문자열의 괄호가 올바르게 짝지어져 있는지 확인하세요.

```python
def is_valid_parentheses(s):
    """괄호 유효성 검사"""
    stack = []
    mapping = {')': '(', '}': '{', ']': '['}
    
    for char in s:
        if char in mapping:  # 닫는 괄호
            if not stack or stack.pop() != mapping[char]:
                return False
        else:  # 여는 괄호
            stack.append(char)
    
    return len(stack) == 0

def is_valid_extended(s):
    """확장된 괄호 검사 (다른 문자 포함)"""
    stack = []
    pairs = {'(': ')', '{': '}', '[': ']'}
    
    for char in s:
        if char in pairs:  # 여는 괄호
            stack.append(pairs[char])
        elif char in pairs.values():  # 닫는 괄호
            if not stack or stack.pop() != char:
                return False
    
    return len(stack) == 0

# 테스트
test_cases = [
    "()",          # True
    "()[]{}",      # True
    "(]",          # False
    "([{}])",      # True
    "(((",         # False
]

for test in test_cases:
    print(f"'{test}' -> {is_valid_parentheses(test)}")
```

### 문제 8: 스택으로 큐 구현

**문제**: 두 개의 스택을 사용하여 큐를 구현하세요.

```python
class MyQueue:
    """스택 두 개로 큐 구현"""
    
    def __init__(self):
        self.stack_in = []   # 입력용 스택
        self.stack_out = []  # 출력용 스택
    
    def push(self, x):
        """큐에 원소 추가"""
        self.stack_in.append(x)
    
    def pop(self):
        """큐에서 원소 제거 및 반환"""
        self._move_to_out()
        if self.stack_out:
            return self.stack_out.pop()
        return None
    
    def peek(self):
        """큐의 첫 번째 원소 확인"""
        self._move_to_out()
        if self.stack_out:
            return self.stack_out[-1]
        return None
    
    def empty(self):
        """큐가 비어있는지 확인"""
        return len(self.stack_in) == 0 and len(self.stack_out) == 0
    
    def _move_to_out(self):
        """입력 스택의 모든 원소를 출력 스택으로 이동"""
        if not self.stack_out:
            while self.stack_in:
                self.stack_out.append(self.stack_in.pop())

# 테스트
queue = MyQueue()
queue.push(1)
queue.push(2)
print(f"peek: {queue.peek()}")  # 1
print(f"pop: {queue.pop()}")    # 1
print(f"empty: {queue.empty()}")  # False
```

## 5. 동적 계획법 기초

### 문제 9: 피보나치 수열

**문제**: n번째 피보나치 수를 구하세요.

```python
def fibonacci_recursive(n):
    """재귀 (비효율적) - O(2^n)"""
    if n <= 1:
        return n
    return fibonacci_recursive(n-1) + fibonacci_recursive(n-2)

def fibonacci_memoization(n, memo=None):
    """메모이제이션 - O(n)"""
    if memo is None:
        memo = {}
    
    if n in memo:
        return memo[n]
    
    if n <= 1:
        return n
    
    memo[n] = fibonacci_memoization(n-1, memo) + fibonacci_memoization(n-2, memo)
    return memo[n]

def fibonacci_dp(n):
    """동적계획법 (상향식) - O(n), O(1) 공간"""
    if n <= 1:
        return n
    
    prev2, prev1 = 0, 1
    
    for i in range(2, n + 1):
        current = prev1 + prev2
        prev2, prev1 = prev1, current
    
    return prev1

# 테스트
n = 10
print(f"Fibonacci({n}):")
print(f"Recursive: {fibonacci_recursive(n)}")
print(f"Memoization: {fibonacci_memoization(n)}")
print(f"DP: {fibonacci_dp(n)}")
```

### 문제 10: 계단 오르기

**문제**: n개의 계단을 1칸 또는 2칸씩 올라갈 수 있을 때, 가능한 방법의 수를 구하세요.

```python
def climb_stairs_recursive(n):
    """재귀 해법"""
    if n <= 2:
        return n
    return climb_stairs_recursive(n-1) + climb_stairs_recursive(n-2)

def climb_stairs_dp(n):
    """동적계획법 해법"""
    if n <= 2:
        return n
    
    dp = [0] * (n + 1)
    dp[1], dp[2] = 1, 2
    
    for i in range(3, n + 1):
        dp[i] = dp[i-1] + dp[i-2]
    
    return dp[n]

def climb_stairs_optimized(n):
    """공간 최적화 해법"""
    if n <= 2:
        return n
    
    prev2, prev1 = 1, 2
    
    for i in range(3, n + 1):
        current = prev1 + prev2
        prev2, prev1 = prev1, current
    
    return prev1

# 테스트
for i in range(1, 6):
    print(f"climb_stairs({i}) = {climb_stairs_optimized(i)}")
```

## 6. 그래프 탐색 기초

### 문제 11: BFS/DFS 구현

**문제**: 그래프에서 BFS와 DFS를 구현하세요.

```python
from collections import deque, defaultdict

class Graph:
    """그래프 클래스"""
    
    def __init__(self):
        self.graph = defaultdict(list)
    
    def add_edge(self, u, v):
        """간선 추가 (무방향 그래프)"""
        self.graph[u].append(v)
        self.graph[v].append(u)
    
    def bfs(self, start):
        """너비 우선 탐색"""
        visited = set()
        queue = deque([start])
        result = []
        
        while queue:
            node = queue.popleft()
            if node not in visited:
                visited.add(node)
                result.append(node)
                
                # 인접 노드를 큐에 추가
                for neighbor in self.graph[node]:
                    if neighbor not in visited:
                        queue.append(neighbor)
        
        return result
    
    def dfs_recursive(self, start, visited=None, result=None):
        """깊이 우선 탐색 (재귀)"""
        if visited is None:
            visited = set()
        if result is None:
            result = []
        
        visited.add(start)
        result.append(start)
        
        for neighbor in self.graph[start]:
            if neighbor not in visited:
                self.dfs_recursive(neighbor, visited, result)
        
        return result
    
    def dfs_iterative(self, start):
        """깊이 우선 탐색 (반복)"""
        visited = set()
        stack = [start]
        result = []
        
        while stack:
            node = stack.pop()
            if node not in visited:
                visited.add(node)
                result.append(node)
                
                # 인접 노드를 스택에 추가 (역순으로 추가해서 알파벳 순서 유지)
                for neighbor in reversed(self.graph[node]):
                    if neighbor not in visited:
                        stack.append(neighbor)
        
        return result

# 테스트
g = Graph()
edges = [(0, 1), (0, 2), (1, 2), (2, 3), (3, 4)]
for u, v in edges:
    g.add_edge(u, v)

print("Graph edges:", edges)
print(f"BFS from 0: {g.bfs(0)}")
print(f"DFS (recursive) from 0: {g.dfs_recursive(0)}")
print(f"DFS (iterative) from 0: {g.dfs_iterative(0)}")
```

## 7. 실전 문제 해결

### 문제 12: 최대 부분 배열 (카데인 알고리즘)

**문제**: 배열에서 연속된 부분 배열의 최대 합을 구하세요.

```python
def max_subarray_brute_force(nums):
    """무차별 대입법 - O(N³)"""
    max_sum = float('-inf')
    n = len(nums)
    
    for i in range(n):
        for j in range(i, n):
            current_sum = sum(nums[i:j+1])
            max_sum = max(max_sum, current_sum)
    
    return max_sum

def max_subarray_optimized(nums):
    """최적화된 해법 - O(N²)"""
    max_sum = float('-inf')
    n = len(nums)
    
    for i in range(n):
        current_sum = 0
        for j in range(i, n):
            current_sum += nums[j]
            max_sum = max(max_sum, current_sum)
    
    return max_sum

def max_subarray_kadane(nums):
    """카데인 알고리즘 - O(N)"""
    max_sum = current_sum = nums[0]
    
    for num in nums[1:]:
        # 현재 원소를 새로운 시작점으로 할지, 이전 합에 추가할지 결정
        current_sum = max(num, current_sum + num)
        max_sum = max(max_sum, current_sum)
    
    return max_sum

def max_subarray_with_indices(nums):
    """최대 부분 배열과 인덱스 반환"""
    max_sum = current_sum = nums[0]
    start = end = 0
    temp_start = 0
    
    for i in range(1, len(nums)):
        if current_sum < 0:
            current_sum = nums[i]
            temp_start = i
        else:
            current_sum += nums[i]
        
        if current_sum > max_sum:
            max_sum = current_sum
            start = temp_start
            end = i
    
    return max_sum, start, end

# 테스트
nums = [-2, 1, -3, 4, -1, 2, 1, -5, 4]
print(f"Array: {nums}")
print(f"Max subarray sum: {max_subarray_kadane(nums)}")

max_sum, start, end = max_subarray_with_indices(nums)
print(f"Max sum: {max_sum}, from index {start} to {end}")
print(f"Subarray: {nums[start:end+1]}")
```

## 코딩테스트 실전 팁

### 1. 문제 접근 전략

```python
def solve_problem_template(problem):
    """문제 해결 템플릿"""
    
    # 1. 문제 이해
    # - 입력과 출력 형태 파악
    # - 제약 조건 확인
    # - 예제 케이스 분석
    
    # 2. 접근 방법 선택
    # - 완전 탐색 vs 그리디 vs DP vs 그래프
    # - 시간/공간 복잡도 계산
    
    # 3. 구현
    # - 단계별로 나누어 구현
    # - 엣지 케이스 고려
    
    # 4. 테스트
    # - 예제 케이스로 검증
    # - 경계값 테스트
    
    pass
```

### 2. 자주 실수하는 부분

```python
# 잘못된 예제들
def common_mistakes():
    # 1. 인덱스 에러
    arr = [1, 2, 3]
    # 잘못: arr[len(arr)]  # IndexError
    # 올바름: arr[len(arr) - 1]
    
    # 2. 무한 루프
    i = 0
    while i < 10:
        print(i)
        # i += 1 을 빼먹음
    
    # 3. 정수 나눗셈
    # Python 3에서 / 는 float 반환
    # 정수 나눗셈은 //
    print(7 // 3)  # 2
    print(7 / 3)   # 2.333...
    
    # 4. 리스트 복사
    original = [1, 2, 3]
    # 잘못: copy = original (참조 복사)
    # 올바름: copy = original.copy() 또는 original[:]
    
    # 5. 딕셔너리 키 존재 확인
    d = {'a': 1}
    # 잘못: if d['b']:  # KeyError
    # 올바름: if 'b' in d: 또는 d.get('b', 0)
```

### 3. 유용한 파이썬 내장 함수

```python
def useful_functions():
    """코딩테스트에 유용한 파이썬 함수들"""
    
    # 정렬
    arr = [3, 1, 4, 1, 5]
    sorted_arr = sorted(arr)  # 새로운 리스트 반환
    arr.sort()  # 제자리 정렬
    
    # 역정렬
    arr.sort(reverse=True)
    
    # 키 함수로 정렬
    words = ["banana", "pie", "Washington", "book"]
    words.sort(key=len)  # 길이순 정렬
    
    # 최대값, 최소값
    print(max(arr), min(arr))
    print(max(enumerate(arr), key=lambda x: x[1]))  # (인덱스, 값)
    
    # 합계
    print(sum(arr))
    print(sum(arr, 10))  # 초기값 10
    
    # 카운팅
    from collections import Counter
    counter = Counter("hello world")
    print(counter.most_common(3))  # 가장 빈번한 3개
    
    # 조합과 순열
    from itertools import combinations, permutations
    print(list(combinations([1, 2, 3], 2)))  # 조합
    print(list(permutations([1, 2, 3], 2)))  # 순열
    
    # 아스키 코드 변환
    print(ord('A'))  # 65
    print(chr(65))   # 'A'
    
    # 진법 변환
    print(bin(10))  # '0b1010'
    print(oct(10))  # '0o12'
    print(hex(10))  # '0xa'
    print(int('1010', 2))  # 10 (2진수 -> 10진수)
```

## 연습 사이트 추천

### 1. 국내 사이트
- **백준(BOJ)**: 다양한 난이도의 문제
- **프로그래머스**: 기업 코딩테스트 기출문제
- **SWEA**: 삼성 SW Expert Academy

### 2. 해외 사이트
- **LeetCode**: 대기업 면접 문제
- **HackerRank**: 체계적인 학습 경로
- **Codeforces**: 대회 형태의 문제

## 학습 로드맵

```python
def study_roadmap():
    """코딩테스트 학습 로드맵"""
    
    roadmap = {
        "1주차": [
            "기본 자료구조 (리스트, 딕셔너리, 셋)",
            "문자열 처리",
            "시간복잡도 이해"
        ],
        "2주차": [
            "정렬 알고리즘",
            "이진 탐색",
            "투 포인터"
        ],
        "3주차": [
            "스택, 큐",
            "해시맵",
            "그리디 알고리즘"
        ],
        "4주차": [
            "재귀",
            "백트래킹",
            "동적계획법 기초"
        ],
        "5주차": [
            "그래프 탐색 (BFS, DFS)",
            "트리 순회",
            "최단경로 (다익스트라)"
        ],
        "6주차": [
            "고급 동적계획법",
            "분할정복",
            "실전 문제 풀이"
        ]
    }
    
    for week, topics in roadmap.items():
        print(f"{week}: {', '.join(topics)}")

study_roadmap()
```

## 결론

코딩테스트는 **꾸준한 연습**이 가장 중요합니다. 다음 원칙들을 기억하세요:

### 🎯 **핵심 원칙**

1. **문제 이해가 우선**: 성급하게 코딩하지 말고 문제를 정확히 파악하세요
2. **시간복잡도 체크**: 제한 시간 내에 실행될 수 있는지 확인하세요
3. **단계적 접근**: 무차별 대입법부터 시작해서 점진적으로 최적화하세요
4. **엣지 케이스 고려**: 빈 배열, 크기가 1인 배열 등을 항상 체크하세요
5. **코드 가독성**: 변수명과 함수명을 명확하게 작성하세요

### 💡 **추가 팁**

- **매일 1-2문제씩 꾸준히** 풀기
- **다양한 해법** 고민해보기
- **시간 제한** 두고 연습하기
- **코드 리뷰** 하고 개선점 찾기
- **기출문제** 위주로 연습하기

파이썬의 강력한 내장 함수들과 라이브러리들을 잘 활용하면 더 간결하고 효율적인 코드를 작성할 수 있습니다. 기초를 탄탄히 다지고 꾸준히 연습한다면 반드시 좋은 결과를 얻을 수 있을 것입니다! 🚀

---

*이 포스트가 도움이 되셨다면 GitHub에서 ⭐️를 눌러주세요!*
