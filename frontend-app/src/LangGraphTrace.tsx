import React, { useState, useEffect } from 'react';

interface StepInfo {
  step: string;
  status: 'success' | 'error' | 'running';
  timestamp: string;
  duration_ms?: number;
  input?: any;
  output?: any;
  error?: string;
}

interface ExecutionTrace {
  total_steps: number;
  steps: StepInfo[];
  errors: string[];
  execution_time: string;
}

interface LangGraphTraceProps {
  trace: ExecutionTrace;
  flowType: 'document' | 'query';
}

const LangGraphTrace: React.FC<LangGraphTraceProps> = ({ trace, flowType }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  // 步骤名称映射
  const stepNames: Record<string, string> = {
    'convert_document': '文档转换',
    'chunk_text': '文本分块', 
    'generate_embeddings': '生成嵌入',
    'store_chunks': '存储块',
    'rewrite_query': '查询重写',
    'hybrid_retrieve': '混合检索',
    'filter_chunks': '相关性过滤',
    'generate_response': '生成回答'
  };

  // 自动播放执行轨迹
  useEffect(() => {
    if (isPlaying && currentStep < trace.steps.length - 1) {
      const timer = setTimeout(() => {
        setCurrentStep(prev => prev + 1);
      }, 1500);
      return () => clearTimeout(timer);
    } else if (currentStep >= trace.steps.length - 1) {
      setIsPlaying(false);
    }
  }, [isPlaying, currentStep, trace.steps.length]);

  const handlePlay = () => {
    setIsPlaying(true);
    setCurrentStep(0);
  };

  const handleStop = () => {
    setIsPlaying(false);
  };

  const handleStepClick = (stepIndex: number) => {
    setCurrentStep(stepIndex);
    setIsPlaying(false);
  };

  return (
    <div className="langgraph-trace">

      {/* 流程图可视化 */}
      <div className="flow-diagram">
        <div className="flow-nodes">
          {trace.steps.map((step, index) => (
            <div
              key={step.step}
              className={`flow-node ${index <= currentStep ? 'active' : ''} ${step.status}`}
              onClick={() => handleStepClick(index)}
            >
              <div className="node-icon">
                {step.status === 'success' ? '✅' : 
                 step.status === 'error' ? '❌' : '⏳'}
              </div>
              <div className="node-label">
                {stepNames[step.step] || step.step}
              </div>
              {step.duration_ms && (
                <div className="node-duration">
                  {step.duration_ms}ms
                </div>
              )}
            </div>
          ))}
        </div>
        
        {/* 连接线 */}
        <div className="flow-connections">
          {trace.steps.slice(0, -1).map((_, index) => (
            <div
              key={index}
              className={`connection ${index < currentStep ? 'active' : ''}`}
            />
          ))}
        </div>
      </div>

      {/* 步骤详情 */}
      <div className="step-details">
        {trace.steps[currentStep] && (
          <div className="step-info">
            <h4>步骤 {currentStep + 1}: {stepNames[trace.steps[currentStep].step]}</h4>
            <div className="step-meta">
              <span className="status">{trace.steps[currentStep].status}</span>
              <span className="timestamp">{trace.steps[currentStep].timestamp}</span>
              {trace.steps[currentStep].duration_ms && (
                <span className="duration">{trace.steps[currentStep].duration_ms}ms</span>
              )}
            </div>
            
            {trace.steps[currentStep].input && (
              <div className="step-input">
                <h5>输入:</h5>
                <pre>{JSON.stringify(trace.steps[currentStep].input, null, 2)}</pre>
              </div>
            )}
            
            {trace.steps[currentStep].output && (
              <div className="step-output">
                <h5>输出:</h5>
                {(() => {
                  const step = trace.steps[currentStep];
                  const output = step.output;
                  
                  // 对于文档转换步骤，显示完整的文本内容
                  if (step.step === 'convert_document' && output.preview) {
                    return (
                      <div>
                        <div className="output-summary">
                          <strong>文本长度:</strong> {output.text_length} 字符
                        </div>
                        <div className="output-content">
                          <strong>内容预览:</strong>
                          <pre style={{ 
                            whiteSpace: 'pre-wrap', 
                            wordWrap: 'break-word',
                            maxHeight: '300px',
                            overflow: 'auto',
                            backgroundColor: '#f8f9fa',
                            padding: '10px',
                            borderRadius: '4px',
                            border: '1px solid #e9ecef'
                          }}>
                            {output.preview}
                          </pre>
                        </div>
                      </div>
                    );
                  }
                  
                  // 对于文本分块步骤，显示所有分块
                  if (step.step === 'chunk_text' && (output.chunks || output.chunk_preview)) {
                    return (
                      <div>
                        <div className="output-summary">
                          <strong>分块数量:</strong> {output.chunk_count} 个
                        </div>
                        <div className="output-content">
                          <strong>所有分块预览:</strong>
                          <div style={{ maxHeight: '400px', overflow: 'auto' }}>
                            {output.chunks ? (
                              // 新格式：显示所有分块
                              output.chunks.map((chunk: string, index: number) => (
                                <div key={index} style={{
                                  marginBottom: '15px',
                                  border: '1px solid #e9ecef',
                                  borderRadius: '6px',
                                  overflow: 'hidden'
                                }}>
                                  <div style={{
                                    backgroundColor: '#f8f9fa',
                                    padding: '8px 12px',
                                    borderBottom: '1px solid #e9ecef',
                                    fontWeight: 'bold',
                                    fontSize: '14px',
                                    color: '#495057'
                                  }}>
                                    分块 {index + 1} (长度: {chunk.length} 字符)
                                  </div>
                                  <pre style={{ 
                                    whiteSpace: 'pre-wrap', 
                                    wordWrap: 'break-word',
                                    margin: 0,
                                    padding: '12px',
                                    backgroundColor: '#ffffff',
                                    fontSize: '13px',
                                    lineHeight: '1.4'
                                  }}>
                                    {chunk}
                                  </pre>
                                </div>
                              ))
                            ) : (
                              // 旧格式：显示预览信息
                              <div style={{
                                marginBottom: '15px',
                                border: '1px solid #e9ecef',
                                borderRadius: '6px',
                                overflow: 'hidden'
                              }}>
                                <div style={{
                                  backgroundColor: '#f8f9fa',
                                  padding: '8px 12px',
                                  borderBottom: '1px solid #e9ecef',
                                  fontWeight: 'bold',
                                  fontSize: '14px',
                                  color: '#495057'
                                }}>
                                  分块预览 (旧格式数据)
                                </div>
                                <pre style={{ 
                                  whiteSpace: 'pre-wrap', 
                                  wordWrap: 'break-word',
                                  margin: 0,
                                  padding: '12px',
                                  backgroundColor: '#ffffff',
                                  fontSize: '13px',
                                  lineHeight: '1.4'
                                }}>
                                  {output.chunk_preview}
                                </pre>
                                <div style={{
                                  padding: '8px 12px',
                                  backgroundColor: '#fff3cd',
                                  borderTop: '1px solid #ffeaa7',
                                  fontSize: '12px',
                                  color: '#856404'
                                }}>
                                  💡 提示：请重新上传文件以查看完整的分块信息
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  }
                  
                  // 对于其他步骤，使用默认的JSON显示
                  return <pre>{JSON.stringify(output, null, 2)}</pre>;
                })()}
              </div>
            )}
            
            {trace.steps[currentStep].error && (
              <div className="step-error">
                <h5>错误:</h5>
                <pre>{trace.steps[currentStep].error}</pre>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 执行统计 */}
      <div className="execution-stats">
        <div className="stat-item">
          <span className="stat-label">总步骤数:</span>
          <span className="stat-value">{trace.total_steps}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">执行时间:</span>
          <span className="stat-value">{trace.execution_time}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">错误数:</span>
          <span className="stat-value">{trace.errors.length}</span>
        </div>
      </div>

      {/* 错误列表 */}
      {trace.errors.length > 0 && (
        <div className="error-list">
          <h4>错误列表:</h4>
          <ul>
            {trace.errors.map((error, index) => (
              <li key={index} className="error-item">{error}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default LangGraphTrace;
