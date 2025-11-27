'use client';

import { useState } from 'react';
import Link from 'next/link';

// FAQ 아코디언 컴포넌트
function FAQItem({ question, answer, isOpen, onClick }: {
  question: string;
  answer: string;
  isOpen: boolean;
  onClick: () => void;
}) {
  return (
    <div className="border-b border-gray-200">
      <button
        className="w-full py-5 px-6 flex justify-between items-center text-left hover:bg-gray-50 transition-colors"
        onClick={onClick}
      >
        <span className="text-lg font-medium text-gray-800">{question}</span>
        <svg
          className={`w-5 h-5 text-blue-600 transform transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {isOpen && (
        <div className="px-6 pb-5 text-gray-600 leading-relaxed">
          {answer}
        </div>
      )}
    </div>
  );
}

// 프로세스 단계 컴포넌트
function ProcessStep({ step, title, description, icon }: {
  step: number;
  title: string;
  description: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center text-center group">
      <div className="relative">
        <div className="w-20 h-20 bg-blue-600 rounded-full flex items-center justify-center mb-4 group-hover:bg-blue-700 transition-colors shadow-lg">
          {icon}
        </div>
        <div className="absolute -top-2 -right-2 w-8 h-8 bg-white border-2 border-blue-600 rounded-full flex items-center justify-center text-blue-600 font-bold text-sm shadow">
          {step}
        </div>
      </div>
      <h4 className="text-lg font-bold text-gray-800 mb-2">{title}</h4>
      <p className="text-gray-600 text-sm">{description}</p>
    </div>
  );
}

// 라운지 카드 컴포넌트
function LoungeCard({ title, subtitle, description, features, href, color }: {
  title: string;
  subtitle: string;
  description: string;
  features: string[];
  href: string;
  color: 'blue' | 'green' | 'purple';
}) {
  const colorClasses = {
    blue: 'from-blue-600 to-blue-800 hover:from-blue-700 hover:to-blue-900',
    green: 'from-emerald-600 to-emerald-800 hover:from-emerald-700 hover:to-emerald-900',
    purple: 'from-violet-600 to-violet-800 hover:from-violet-700 hover:to-violet-900',
  };

  return (
    <div className="bg-white rounded-2xl shadow-lg overflow-hidden hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1">
      <div className={`bg-gradient-to-r ${colorClasses[color]} p-6 text-white`}>
        <p className="text-sm opacity-80 mb-1">{subtitle}</p>
        <h3 className="text-2xl font-bold">{title}</h3>
      </div>
      <div className="p-6">
        <p className="text-gray-600 mb-4">{description}</p>
        <ul className="space-y-2 mb-6">
          {features.map((feature, index) => (
            <li key={index} className="flex items-center text-gray-700">
              <svg className="w-5 h-5 text-green-500 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span className="text-sm">{feature}</span>
            </li>
          ))}
        </ul>
        <Link
          href={href}
          className={`inline-block w-full text-center py-3 px-6 rounded-lg font-semibold text-white bg-gradient-to-r ${colorClasses[color]} transition-all`}
        >
          바로가기
        </Link>
      </div>
    </div>
  );
}

export default function LandingPage() {
  const [openFAQ, setOpenFAQ] = useState<number | null>(0);

  const faqs = [
    {
      question: '이 서비스는 무엇인가요?',
      answer: 'AI 기반 기업 재무 진단 플랫폼으로, 37개 재무 데이터를 분석하여 부도 위험 예측, 동종 기업 비교, 협력사 추천까지 제공합니다. 머신러닝 모델(CatBoost)과 딥러닝 기반 클러스터링(Beta-VAE + HDBSCAN)을 활용합니다.',
    },
    {
      question: '어떤 기업이 사용 가능한가요?',
      answer: '재무제표를 보유한 모든 기업이 사용 가능합니다. 특히 중소기업, 스타트업, 협력사 관리가 필요한 대기업에 적합합니다. 업종에 관계없이 제조업, 서비스업, 유통업 등 모든 업종을 지원합니다.',
    },
    {
      question: '분석에 필요한 데이터는 무엇인가요?',
      answer: '기본적인 재무비율 37개 항목이 필요합니다. 유동비율, 부채비율, ROA, ROE 등 안정성/수익성/성장성/활동성/현금흐름 관련 지표를 포함합니다. 엑셀 템플릿을 다운받아 쉽게 입력할 수 있습니다.',
    },
    {
      question: '분석 결과는 어떻게 활용할 수 있나요?',
      answer: '신용평가 자료, 투자 의사결정, 협력사 선정, 자체 경영진단 등에 활용할 수 있습니다. 부도확률 예측 결과와 SHAP 분석을 통해 어떤 재무지표가 위험 요인인지 파악할 수 있고, 클러스터 분석으로 시장 내 위치를 확인할 수 있습니다.',
    },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Hero Section - BASA 스타일 */}
      <section className="relative bg-gradient-to-br from-slate-900 via-blue-900 to-slate-800 text-white overflow-hidden">
        {/* 배경 패턴 */}
        <div className="absolute inset-0 opacity-10 pointer-events-none">
          <div className="absolute top-0 left-0 w-96 h-96 bg-blue-500 rounded-full filter blur-3xl"></div>
          <div className="absolute bottom-0 right-0 w-96 h-96 bg-indigo-500 rounded-full filter blur-3xl"></div>
        </div>

        <div className="relative container mx-auto px-4 py-24 max-w-6xl">
          <div className="text-center">
            <p className="text-blue-300 text-sm font-medium mb-4 tracking-wider">
              AI-POWERED FINANCIAL DIAGNOSIS PLATFORM
            </p>
            <h1 className="text-4xl md:text-6xl font-bold mb-6 leading-tight">
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-300 to-cyan-300">
                C.O.R.E
              </span>
              <span className="block text-2xl md:text-3xl mt-2 text-blue-100">
                Corporate Optimization Risk Evaluation
              </span>
            </h1>
            <p className="text-xl text-blue-100 mb-10 max-w-2xl mx-auto">
              엑셀 하나로 부도 위험 예측 · 동종업계 비교 · 우량 협력사 추천까지
            </p>

            <div className="flex justify-center relative z-10">
              <Link
                href="/upload"
                className="inline-flex items-center justify-center bg-white text-blue-900 px-10 py-5 rounded-xl text-xl font-bold
                         hover:bg-blue-50 transition-all duration-300 shadow-lg hover:shadow-xl
                         transform hover:-translate-y-1 cursor-pointer"
              >
                <svg className="w-7 h-7 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
                경영진단 시작하기
              </Link>
            </div>

            <p className="text-blue-300/70 mt-6 text-sm">
              회원가입 없이 바로 시작 가능 · 데이터는 분석 후 자동 삭제
            </p>
          </div>
        </div>

        {/* 하단 웨이브 */}
        <div className="absolute bottom-0 left-0 right-0 pointer-events-none">
          <svg viewBox="0 0 1440 120" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M0 120L60 110C120 100 240 80 360 70C480 60 600 60 720 65C840 70 960 80 1080 85C1200 90 1320 90 1380 90L1440 90V120H1380C1320 120 1200 120 1080 120C960 120 840 120 720 120C600 120 480 120 360 120C240 120 120 120 60 120H0Z" fill="#F9FAFB"/>
          </svg>
        </div>
      </section>

      {/* FAQ Section - BASA 스타일 아코디언 */}
      <section className="py-16 px-4 bg-gray-50">
        <div className="container mx-auto max-w-3xl">
          <h2 className="text-3xl font-bold text-center text-gray-800 mb-2">
            자주 묻는 질문
          </h2>
          <p className="text-gray-500 text-center mb-10">
            서비스에 대해 궁금한 점을 확인하세요
          </p>

          <div className="bg-white rounded-2xl shadow-lg overflow-hidden">
            {faqs.map((faq, index) => (
              <FAQItem
                key={index}
                question={faq.question}
                answer={faq.answer}
                isOpen={openFAQ === index}
                onClick={() => setOpenFAQ(openFAQ === index ? null : index)}
              />
            ))}
          </div>
        </div>
      </section>

      {/* Process Steps - 4단계 프로세스 */}
      <section className="py-20 px-4 bg-white">
        <div className="container mx-auto max-w-6xl">
          <h2 className="text-3xl font-bold text-center text-gray-800 mb-4">
            진단 프로세스
          </h2>
          <p className="text-gray-500 text-center mb-16">
            4단계로 간편하게 기업 재무 진단을 받아보세요
          </p>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 relative">
            {/* 연결선 (데스크톱) */}
            <div className="hidden md:block absolute top-10 left-[12.5%] right-[12.5%] h-0.5 bg-blue-200 z-0"></div>

            <ProcessStep
              step={1}
              title="템플릿 다운로드"
              description="표준화된 엑셀 템플릿을 다운로드합니다"
              icon={<svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>}
            />
            <ProcessStep
              step={2}
              title="재무데이터 입력"
              description="37개 재무비율 데이터를 입력합니다"
              icon={<svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>}
            />
            <ProcessStep
              step={3}
              title="파일 업로드"
              description="작성한 엑셀 파일을 업로드합니다"
              icon={<svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>}
            />
            <ProcessStep
              step={4}
              title="결과 확인"
              description="AI 분석 결과를 즉시 확인합니다"
              icon={<svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>}
            />
          </div>

          <div className="text-center mt-12">
            <Link
              href="/upload"
              className="inline-flex items-center justify-center bg-blue-600 text-white px-8 py-4 rounded-xl text-lg font-semibold
                       hover:bg-blue-700 transition-all duration-300 shadow-lg"
            >
              지금 바로 시작하기
              <svg className="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </Link>
          </div>
        </div>
      </section>

      {/* Service Lounges - BASA 스타일 라운지 섹션 */}
      <section className="py-20 px-4 bg-gray-100">
        <div className="container mx-auto max-w-6xl">
          <h2 className="text-3xl font-bold text-center text-gray-800 mb-4">
            서비스 라운지
          </h2>
          <p className="text-gray-500 text-center mb-12">
            목적에 맞는 분석 서비스를 선택하세요
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <LoungeCard
              title="부도예측 분석"
              subtitle="Default Prediction"
              description="AI 모델이 기업의 부도 가능성을 예측하고, 주요 위험 요인을 분석합니다."
              features={[
                'CatBoost 기반 부도확률 예측',
                'SHAP 분석으로 위험요인 파악',
                '신용등급 산정 기준 제공',
                '업종별 평균 대비 비교',
              ]}
              href="/upload"
              color="blue"
            />

            <LoungeCard
              title="기업 클러스터링"
              subtitle="Business Clustering"
              description="유사한 재무 특성을 가진 기업군을 찾아 시장 내 위치를 파악합니다."
              features={[
                'Beta-VAE + HDBSCAN 클러스터링',
                '13개 기업군 분류 분석',
                '레이더 차트 프로파일링',
                '클러스터별 특성 비교',
              ]}
              href="/upload"
              color="green"
            />

            <LoungeCard
              title="협력사 추천"
              subtitle="Partner Recommendation"
              description="같은 기업군 내 재무가 우량한 기업을 협력사 후보로 추천합니다."
              features={[
                '동일 클러스터 내 우량 기업 추천',
                '재무 안정성 기반 랭킹',
                '업종/규모 필터링 가능',
                '협력사 리스크 관리',
              ]}
              href="/upload"
              color="purple"
            />
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-16 px-4 bg-white">
        <div className="container mx-auto max-w-6xl">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            <div className="text-center">
              <div className="text-4xl font-bold text-blue-600 mb-2">50,000+</div>
              <div className="text-gray-600">학습 데이터</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-blue-600 mb-2">37개</div>
              <div className="text-gray-600">재무 지표 분석</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-blue-600 mb-2">74.7%</div>
              <div className="text-gray-600">예측 정확도 (AUC)</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-blue-600 mb-2">13개</div>
              <div className="text-gray-600">기업군 클러스터</div>
            </div>
          </div>
        </div>
      </section>

      {/* Dashboard Preview Link */}
      <section className="py-16 px-4 bg-gray-50">
        <div className="container mx-auto max-w-4xl text-center">
          <h2 className="text-2xl font-bold text-gray-800 mb-4">
            시장 현황이 궁금하신가요?
          </h2>
          <p className="text-gray-600 mb-8">
            전체 기업 데이터 기반 신용등급 분포, 업종별 부도율 등을 대시보드에서 확인하세요
          </p>
          <Link
            href="/dashboard"
            className="inline-flex items-center text-blue-600 hover:text-blue-700 font-semibold text-lg"
          >
            대시보드 보러가기
            <svg className="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </Link>
        </div>
      </section>

      {/* Final CTA Section */}
      <section className="py-20 px-4 bg-gradient-to-r from-blue-900 to-indigo-900 text-white">
        <div className="container mx-auto max-w-4xl text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-6">
            지금 바로 기업 진단을 시작하세요
          </h2>
          <p className="text-blue-100 text-lg mb-10 max-w-2xl mx-auto">
            엑셀 템플릿에 재무 데이터를 입력하고 업로드하면<br />
            AI가 부도 위험, 시장 내 위치, 추천 협력사를 분석해 드립니다.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/upload"
              className="inline-flex items-center justify-center bg-white text-blue-900 px-8 py-4 rounded-xl text-lg font-bold
                       hover:bg-blue-50 transition-all duration-300 shadow-lg"
            >
              무료 경영진단 시작하기
            </Link>
            <a
              href="/api/v1/predict/template"
              className="inline-flex items-center justify-center border-2 border-white/30 text-white px-8 py-4 rounded-xl text-lg font-semibold
                       hover:bg-white/10 transition-all duration-300"
            >
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              템플릿 다운로드
            </a>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-slate-900 text-gray-400 py-12 px-4">
        <div className="container mx-auto max-w-6xl">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div>
              <h3 className="text-white font-bold text-lg mb-4">C.O.R.E</h3>
              <p className="text-sm leading-relaxed">
                Corporate Optimization Risk Evaluation - AI 기반 부도 예측 및 기업 분석 서비스를 제공합니다.
                머신러닝과 딥러닝 기술을 활용하여 정확한 재무 진단 결과를 제공합니다.
              </p>
            </div>
            <div>
              <h3 className="text-white font-bold text-lg mb-4">서비스</h3>
              <ul className="space-y-2 text-sm">
                <li><Link href="/upload" className="hover:text-white transition-colors">경영진단 신청</Link></li>
                <li><Link href="/result" className="hover:text-white transition-colors">결과 조회</Link></li>
                <li><Link href="/dashboard" className="hover:text-white transition-colors">시장 현황 대시보드</Link></li>
              </ul>
            </div>
            <div>
              <h3 className="text-white font-bold text-lg mb-4">기술 스택</h3>
              <ul className="space-y-2 text-sm">
                <li>부도예측: CatBoost + SHAP</li>
                <li>클러스터링: Beta-VAE + HDBSCAN</li>
                <li>시각화: UMAP + Radar Chart</li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 mt-10 pt-8 text-center text-sm">
            <p>&copy; 2024 C.O.R.E. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
