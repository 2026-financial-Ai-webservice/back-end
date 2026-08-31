def build_analysis_prompt(user_input: dict, companies: list[dict]) -> str:
    company_blocks = "\n\n".join(
        f"- {c['company_name']}({c['corp_code']})\n"
        f"  최종점수: {c['final_score']}, PER: {c['per']}, PBR: {c['pbr']},"
        f"시가총액: {c['market_cap']}억원, ROE: {c['roe']}%, "
        f"DCF 상승여력: {c['dcf']}%, 배분비율: {c['allocation_ratio']}%\n"
        f"  사업개요: {c['business_summary']}"
        for c in companies
    )
    return f"""
        다음은 사용자의 투자 성향과, 이를 바탕으로 선정된 포트폴리오 후보 기업들입니다.
        주어진 데이터에 없는 수치는 절대 지어내지 말고, 없으면 언급하지 마세요.
        
        [사용자 투자 성향]
        - 투자기간: {user_input['investment_period']}
        - 위험성향: {user_input['risk_preference']}
        - 수익선호: {user_input['return_preference']}
        - 가치평가선호: {user_input['valuation_preference']}
        
        [후보 기업]
        {company_blocks}
        
        위 정보를 바탕으로 작성해주세요:
        1. valuation_analysis: DCF/PER 관점에서의 밸류에이션 산출 과정을 포트폴리오 전체
           관점에서 요약 (3~4문장, 구체적 수치 인용)
        2. market_indicator_analysis: 시가총액/PER 등 시장 지표 기본 정보 요약 (3~4문장)
        3. allocation_analysis: 왜 이런 비율로 배분했는지 설명 (3~4문장)
    """.strip()

def build_reason_prompt(user_input: dict, companies: list[dict]) -> str:
    company_blocks = "\n\n".join(
        f"- {c['company_name']}({c['corp_code']})\n"
        f"  최종점수: {c['final_score']}, PER: {c['per']}, PBR: {c['pbr']},"
        f"시가총액: {c['market_cap']}억원, ROE: {c['roe']}%, "
        f"DCF 상승여력: {c['dcf']}%, 배분비율: {c['allocation_ratio']}%\n"
        f"  사업개요: {c['business_summary']}"
        for c in companies
    )
    return f"""
        다음은 사용자의 투자 성향과, 이를 바탕으로 선정된 포트폴리오 후보 기업들입니다.
        주어진 데이터에 없는 수치는 절대 지어내지 말고, 없으면 언급하지 마세요.
        
        [사용자 투자 성향]
        - 투자기간: {user_input['investment_period']}
        - 위험성향: {user_input['risk_preference']}
        - 수익선호: {user_input['return_preference']}
        - 가치평가선호: {user_input['valuation_preference']}
        
        [후보 기업]
        {company_blocks}
        
        위 정보를 바탕으로 작성해주세요:
        1. 각 기업별 investment_reason: 왜 이 기업이 선정됐는지 수치를 인용한 한 줄 요약
    """.strip()