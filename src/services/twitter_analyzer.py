"""
推特内容分析器
负责分析推文内容，识别CA地址和其他重要信息
"""

import re
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum

from ..utils.logger import logger


class ContractAddressType(Enum):
    """合约地址类型"""
    ETHEREUM = "ethereum"
    BSC = "bsc" 
    SOLANA = "solana"
    POLYGON = "polygon"
    ARBITRUM = "arbitrum"
    OPTIMISM = "optimism"
    UNKNOWN = "unknown"


@dataclass
class ContractAddress:
    """合约地址信息"""
    address: str
    type: ContractAddressType
    confidence: float  # 识别置信度 0.0-1.0
    context: str  # 地址在推文中的上下文
    position: int  # 在推文中的位置


@dataclass
class AnalysisResult:
    """分析结果"""
    ca_addresses: List[ContractAddress]
    has_ca: bool
    risk_score: float  # 风险评分 0.0-1.0
    keywords_found: List[str]
    sentiment_score: Optional[float] = None


class TwitterAnalyzer:
    """推特内容分析器"""
    
    def __init__(self):
        # 编译正则表达式提高性能
        self._compile_patterns()
        
        # 关键词列表
        self.crypto_keywords = {
            'launch': ['launch', 'launching', '发射', '上线', '启动'],
            'gem': ['gem', '宝石', 'diamond', '钻石', 'alpha'],  
            'moon': ['moon', 'to the moon', '🚀', '月球', 'rocket'],
            'buy': ['buy', 'buying', 'bought', '买入', '购买', 'ape'],
            'sell': ['sell', 'selling', 'sold', '卖出', '出售'],
            'pump': ['pump', 'pumping', '暴涨', '拉盘'],
            'dump': ['dump', 'dumping', '砸盘', '暴跌'],
            'degen': ['degen', 'degen play', 'yolo'],
            'airdrop': ['airdrop', '空投', 'drop'],
            'new_token': ['new token', '新币', 'new coin', 'fresh']
        }
        
        # 风险关键词（用于风险评分）
        self.risk_keywords = {
            'high_risk': ['scam', 'rug', 'honeypot', '诈骗', '跑路', '蜜罐'],
            'medium_risk': ['quick', 'fast', 'urgent', '快速', '紧急', 'fomo'],
            'speculation': ['100x', '1000x', 'moonshot', '百倍', '千倍']
        }
        
    def _compile_patterns(self):
        """编译正则表达式"""
        
        # Ethereum地址格式: 0x + 40位十六进制
        self.eth_pattern = re.compile(
            r'\b0x[a-fA-F0-9]{40}\b',
            re.IGNORECASE
        )
        
        # Solana地址格式: 32-44位Base58字符
        self.solana_pattern = re.compile(
            r'\b[1-9A-HJ-NP-Za-km-z]{32,44}\b'
        )
        
        # BSC地址格式（与Ethereum相同但需要上下文判断）
        self.bsc_pattern = re.compile(
            r'\b0x[a-fA-F0-9]{40}\b',
            re.IGNORECASE
        )
        
        # 其他EVM链地址格式
        self.evm_pattern = re.compile(
            r'\b0x[a-fA-F0-9]{40}\b',
            re.IGNORECASE
        )
        
        # CA地址常见前缀模式
        self.ca_context_patterns = [
            re.compile(r'(ca|contract|address|token)[\s:]*([0-9A-Za-z]{32,44})', re.IGNORECASE),
            re.compile(r'([0-9A-Za-z]{32,44})[\s]*(?:ca|contract|address)', re.IGNORECASE),
            re.compile(r'0x[a-fA-F0-9]{40}', re.IGNORECASE)
        ]
        
    def analyze_tweet(self, tweet_text: str) -> AnalysisResult:
        """
        分析推文内容
        
        Args:
            tweet_text: 推文文本
            
        Returns:
            分析结果
        """
        logger.debug(f"开始分析推文: {tweet_text[:100]}...")
        
        # 识别CA地址
        ca_addresses = self._extract_contract_addresses(tweet_text)
        
        # 关键词匹配
        keywords_found = self._find_keywords(tweet_text)
        
        # 风险评分
        risk_score = self._calculate_risk_score(tweet_text, ca_addresses, keywords_found)
        
        result = AnalysisResult(
            ca_addresses=ca_addresses,
            has_ca=len(ca_addresses) > 0,
            risk_score=risk_score,
            keywords_found=keywords_found
        )
        
        logger.info(f"分析完成: CA数量={len(ca_addresses)}, 关键词={len(keywords_found)}, 风险评分={risk_score:.2f}")
        return result
        
    def _extract_contract_addresses(self, text: str) -> List[ContractAddress]:
        """
        提取合约地址
        
        Args:
            text: 推文文本
            
        Returns:
            识别到的合约地址列表
        """
        addresses = []
        
        # 清理文本，移除多余空格
        clean_text = ' '.join(text.split())
        
        # 1. 提取Ethereum/BSC/其他EVM链地址
        eth_matches = list(self.eth_pattern.finditer(clean_text))
        for match in eth_matches:
            address = match.group().lower()
            start_pos = match.start()
            
            # 获取上下文
            context_start = max(0, start_pos - 50)
            context_end = min(len(clean_text), start_pos + len(address) + 50)
            context = clean_text[context_start:context_end]
            
            # 判断具体链类型
            chain_type = self._determine_evm_chain_type(context)
            confidence = self._calculate_address_confidence(address, context, chain_type)
            
            if confidence > 0.3:  # 置信度阈值
                addresses.append(ContractAddress(
                    address=address,
                    type=chain_type,
                    confidence=confidence,
                    context=context,
                    position=start_pos
                ))
                
        # 2. 提取Solana地址
        solana_matches = list(self.solana_pattern.finditer(clean_text))
        for match in solana_matches:
            address = match.group()
            start_pos = match.start()
            
            # 排除明显不是地址的字符串
            if self._is_likely_solana_address(address):
                context_start = max(0, start_pos - 50)
                context_end = min(len(clean_text), start_pos + len(address) + 50)
                context = clean_text[context_start:context_end]
                
                confidence = self._calculate_address_confidence(address, context, ContractAddressType.SOLANA)
                
                if confidence > 0.3:
                    addresses.append(ContractAddress(
                        address=address,
                        type=ContractAddressType.SOLANA,
                        confidence=confidence,
                        context=context,
                        position=start_pos
                    ))
        
        # 去重（保留置信度最高的）
        unique_addresses = {}
        for addr in addresses:
            if addr.address not in unique_addresses or addr.confidence > unique_addresses[addr.address].confidence:
                unique_addresses[addr.address] = addr
                
        return list(unique_addresses.values())
        
    def _determine_evm_chain_type(self, context: str) -> ContractAddressType:
        """
        根据上下文判断EVM链类型
        
        Args:
            context: 地址上下文
            
        Returns:
            链类型
        """
        context_lower = context.lower()
        
        # BSC关键词
        if any(keyword in context_lower for keyword in ['bsc', 'binance', 'bnb', 'pancake']):
            return ContractAddressType.BSC
            
        # Polygon关键词  
        elif any(keyword in context_lower for keyword in ['polygon', 'matic', 'quickswap']):
            return ContractAddressType.POLYGON
            
        # Arbitrum关键词
        elif any(keyword in context_lower for keyword in ['arbitrum', 'arb', 'camelot']):
            return ContractAddressType.ARBITRUM
            
        # Optimism关键词
        elif any(keyword in context_lower for keyword in ['optimism', 'op', 'velodrome']):
            return ContractAddressType.OPTIMISM
            
        # 默认以太坊
        else:
            return ContractAddressType.ETHEREUM
            
    def _is_likely_solana_address(self, address: str) -> bool:
        """
        判断字符串是否可能是Solana地址
        
        Args:
            address: 候选地址字符串
            
        Returns:
            是否可能是Solana地址
        """
        # 长度检查
        if not 32 <= len(address) <= 44:
            return False
            
        # 排除纯数字、纯字母
        if address.isdigit() or address.isalpha():
            return False
            
        # 排除常见的非地址字符串
        common_false_positives = {
            'http', 'https', 'twitter', 'telegram', 'discord',
            'youtube', 'github', 'medium', 'instagram'
        }
        
        if any(fp in address.lower() for fp in common_false_positives):
            return False
            
        return True
        
    def _calculate_address_confidence(
        self, 
        address: str, 
        context: str, 
        chain_type: ContractAddressType
    ) -> float:
        """
        计算地址识别置信度
        
        Args:
            address: 地址
            context: 上下文
            chain_type: 链类型
            
        Returns:
            置信度分数 (0.0-1.0)
        """
        confidence = 0.5  # 基础分数
        context_lower = context.lower()
        
        # CA关键词提升置信度
        ca_keywords = ['ca:', 'ca ', 'contract', 'address', 'token', '合约']
        if any(keyword in context_lower for keyword in ca_keywords):
            confidence += 0.3
            
        # 链相关关键词
        chain_keywords = {
            ContractAddressType.ETHEREUM: ['eth', 'ethereum', 'uniswap'],
            ContractAddressType.BSC: ['bsc', 'bnb', 'pancake'],
            ContractAddressType.SOLANA: ['sol', 'solana', 'jupiter', 'raydium'],
            ContractAddressType.POLYGON: ['polygon', 'matic'],
            ContractAddressType.ARBITRUM: ['arbitrum', 'arb'],
            ContractAddressType.OPTIMISM: ['optimism', 'op']
        }
        
        if chain_type in chain_keywords:
            if any(keyword in context_lower for keyword in chain_keywords[chain_type]):
                confidence += 0.2
                
        # 交易所/DEX关键词
        dex_keywords = ['dex', 'swap', 'trade', 'buy', 'sell', 'pool']
        if any(keyword in context_lower for keyword in dex_keywords):
            confidence += 0.1
            
        # 时间敏感词降低置信度（可能是误识别）
        time_keywords = ['2024', '2023', 'january', 'february', 'march']
        if any(keyword in context_lower for keyword in time_keywords):
            confidence -= 0.2
            
        return min(1.0, max(0.0, confidence))
        
    def _find_keywords(self, text: str) -> List[str]:
        """
        查找关键词
        
        Args:
            text: 推文文本
            
        Returns:
            找到的关键词类别列表
        """
        found_keywords = []
        text_lower = text.lower()
        
        for category, keywords in self.crypto_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                found_keywords.append(category)
                
        return found_keywords
        
    def _calculate_risk_score(
        self, 
        text: str, 
        ca_addresses: List[ContractAddress], 
        keywords: List[str]
    ) -> float:
        """
        计算风险评分
        
        Args:
            text: 推文文本
            ca_addresses: 识别到的CA地址
            keywords: 找到的关键词
            
        Returns:
            风险评分 (0.0-1.0)
        """
        risk_score = 0.0
        text_lower = text.lower()
        
        # 基于风险关键词
        for category, risk_keywords in self.risk_keywords.items():
            if any(keyword in text_lower for keyword in risk_keywords):
                if category == 'high_risk':
                    risk_score += 0.4
                elif category == 'medium_risk':
                    risk_score += 0.2
                elif category == 'speculation':
                    risk_score += 0.1
                    
        # 多个CA地址增加风险
        if len(ca_addresses) > 1:
            risk_score += 0.1
            
        # 低置信度地址增加风险
        for addr in ca_addresses:
            if addr.confidence < 0.5:
                risk_score += 0.1
                
        # 特定关键词组合增加风险
        risky_combinations = [
            ['pump', 'dump'],
            ['quick', 'money'], 
            ['easy', 'profit']
        ]
        
        for combo in risky_combinations:
            if all(word in text_lower for word in combo):
                risk_score += 0.15
                
        return min(1.0, risk_score)
        
    def get_ca_addresses_as_strings(self, analysis_result: AnalysisResult) -> List[str]:
        """
        获取CA地址字符串列表
        
        Args:
            analysis_result: 分析结果
            
        Returns:
            地址字符串列表
        """
        return [addr.address for addr in analysis_result.ca_addresses]
        
    def filter_high_confidence_addresses(
        self, 
        ca_addresses: List[ContractAddress], 
        min_confidence: float = 0.7
    ) -> List[ContractAddress]:
        """
        过滤高置信度地址
        
        Args:
            ca_addresses: CA地址列表
            min_confidence: 最小置信度阈值
            
        Returns:
            高置信度地址列表
        """
        return [addr for addr in ca_addresses if addr.confidence >= min_confidence]