import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass

@dataclass
class FractalPoint:
    index: int
    price: float
    direction: str  # 'top' or 'bottom'
    time: pd.Timestamp

@dataclass
class Stroke:
    start_point: FractalPoint
    end_point: FractalPoint
    direction: str  # 'up' or 'down'
    high: float
    low: float

@dataclass
class Segment:
    strokes: List[Stroke]
    direction: str  # 'up' or 'down'
    high: float
    low: float

class ChanAnalyzer:
    def __init__(self):
        self.min_stroke_length = 3  # 最小笔长度
        self.min_segment_strokes = 3  # 最小线段包含笔数

    def identify_fractal(self, data: pd.DataFrame, k: int = 3) -> List[FractalPoint]:
        """识别K线分型"""
        fractals = []
        for i in range(k, len(data) - k):
            # 顶分型判断
            if (data['high'].iloc[i-k:i].max() < data['high'].iloc[i] and
                data['high'].iloc[i+1:i+k+1].max() < data['high'].iloc[i]):
                fractals.append(FractalPoint(
                    index=i,
                    price=data['high'].iloc[i],
                    direction='top',
                    time=data.index[i]
                ))
            # 底分型判断
            elif (data['low'].iloc[i-k:i].min() > data['low'].iloc[i] and
                  data['low'].iloc[i+1:i+k+1].min() > data['low'].iloc[i]):
                fractals.append(FractalPoint(
                    index=i,
                    price=data['low'].iloc[i],
                    direction='bottom',
                    time=data.index[i]
                ))
        return fractals

    def create_strokes(self, fractals: List[FractalPoint]) -> List[Stroke]:
        """生成笔"""
        strokes = []
        i = 0
        while i < len(fractals) - 1:
            start_point = fractals[i]
            # 寻找符合条件的结束点
            for j in range(i + 1, len(fractals)):
                end_point = fractals[j]
                if (start_point.direction != end_point.direction and
                    abs(j - i) >= self.min_stroke_length):
                    # 创建新的笔
                    direction = 'up' if start_point.direction == 'bottom' else 'down'
                    stroke = Stroke(
                        start_point=start_point,
                        end_point=end_point,
                        direction=direction,
                        high=max(start_point.price, end_point.price),
                        low=min(start_point.price, end_point.price)
                    )
                    strokes.append(stroke)
                    i = j
                    break
            i += 1
        return strokes

    def create_segments(self, strokes: List[Stroke]) -> List[Segment]:
        """生成线段"""
        segments = []
        i = 0
        while i < len(strokes) - self.min_segment_strokes:
            start_stroke = strokes[i]
            current_direction = start_stroke.direction
            segment_strokes = [start_stroke]
            
            # 寻找线段结束点
            for j in range(i + 1, len(strokes)):
                if strokes[j].direction != current_direction:
                    # 判断是否构成线段转折
                    if len(segment_strokes) >= self.min_segment_strokes:
                        segment = Segment(
                            strokes=segment_strokes,
                            direction=current_direction,
                            high=max(s.high for s in segment_strokes),
                            low=min(s.low for s in segment_strokes)
                        )
                        segments.append(segment)
                        i = j
                        break
                segment_strokes.append(strokes[j])
            i += 1
        return segments

    def identify_pivot(self, segments: List[Segment]) -> List[Dict]:
        """识别中枢"""
        pivots = []
        i = 0
        while i < len(segments) - 3:
            # 寻找连续三段重叠区间
            overlap_high = min(segments[i].high, segments[i+1].high, segments[i+2].high)
            overlap_low = max(segments[i].low, segments[i+1].low, segments[i+2].low)
            
            if overlap_high > overlap_low:
                pivot = {
                    'start_index': i,
                    'end_index': i + 2,
                    'high': overlap_high,
                    'low': overlap_low
                }
                pivots.append(pivot)
            i += 1
        return pivots

    def analyze(self, data: pd.DataFrame) -> Dict:
        """进行完整的缠论分析"""
        try:
            # 识别分型
            fractals = self.identify_fractal(data)
            
            # 生成笔
            strokes = self.create_strokes(fractals)
            
            # 生成线段
            segments = self.create_segments(strokes)
            
            # 识别中枢
            pivots = self.identify_pivot(segments)
            
            # 判断当前趋势
            current_trend = 'up' if segments[-1].direction == 'up' else 'down'
            
            # 计算支撑和阻力位
            if pivots:
                latest_pivot = pivots[-1]
                support = latest_pivot['low']
                resistance = latest_pivot['high']
            else:
                support = min(s.low for s in segments[-3:]) if len(segments) >= 3 else None
                resistance = max(s.high for s in segments[-3:]) if len(segments) >= 3 else None
            
            return {
                'trend': current_trend,
                'support': support,
                'resistance': resistance,
                'latest_pivot': pivots[-1] if pivots else None,
                'stroke_count': len(strokes),
                'segment_count': len(segments)
            }
            
        except Exception as e:
            return {'error': str(e)}