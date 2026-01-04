# Models package
from app.database import Base

# Import all models
from .user import User
from .case import Case, CasePrompt, CaseAnalysis, CaseKPI
from .osint import OSINTQuery, OSINTResult, OSINTSource
from .geopolitical import BilateralRelation, Treaty, DiplomaticEvent, GeopoliticalRisk, SupplyChainRisk, EconomicInterdependence
from .ai_analysis import AIAnalysis, Concept, Trend, Sentiment, AIPrediction
from .ai_classification import AIClassification, ClassificationCategory, ClassificationFeedback, AIModelTraining
from .qualitative import Premise, ReasoningFramework, KPI, QualitativeAnalysis, QuantitativeAnalysis
from .predictions import Prediction, PredictionModel, ConfidenceScore
from .reports import Report
from .investments import InvestmentRecommendation, RiskAnalysis, Opportunity
from .reputation import ReputationProfile, ReputationHistory, StakeholderAnalysis
from .public_affairs import PolicyAnalysis, AdvocacyCampaign

__all__ = [
    "Base",
    "User",
    "Case", "CasePrompt", "CaseAnalysis", "CaseKPI",
    "OSINTQuery", "OSINTResult", "OSINTSource",
    "AIAnalysis", "Concept", "Trend", "Sentiment", "AIPrediction",
    "AIClassification", "ClassificationCategory", "ClassificationFeedback", "AIModelTraining",
    "Premise", "ReasoningFramework", "KPI", "QualitativeAnalysis", "QuantitativeAnalysis",
    "Prediction", "PredictionModel", "ConfidenceScore",
    "Report",
    "InvestmentRecommendation", "RiskAnalysis", "Opportunity",
    "BilateralRelation", "Treaty", "DiplomaticEvent", "GeopoliticalRisk",
    "SupplyChainRisk", "EconomicInterdependence",
    "ReputationProfile", "ReputationHistory", "StakeholderAnalysis",
    "PolicyAnalysis", "AdvocacyCampaign",
]

