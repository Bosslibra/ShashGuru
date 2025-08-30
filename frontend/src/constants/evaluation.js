// Chess evaluation engine constants
export const EVALUATION_CONSTANTS = {
  // Default depth for engine evaluation
  DEFAULT_DEPTH: 20,
  
  // Minimum and maximum depth values
  MIN_DEPTH: 10,
  MAX_DEPTH: 50,
  
  // Default number of engine lines to show
  DEFAULT_SHOW_LINES: 1,
  
  // Minimum and maximum lines to show
  MIN_SHOW_LINES: 1,
  MAX_SHOW_LINES: 5,
  
  // Other evaluation-related defaults
  DEFAULT_EVALUATION_ENABLED: true,
  DEFAULT_SHOW_BEST_MOVE: true
};

// Export individual constants for convenience
export const {
  DEFAULT_DEPTH,
  MIN_DEPTH,
  MAX_DEPTH,
  DEFAULT_SHOW_LINES,
  MIN_SHOW_LINES,
  MAX_SHOW_LINES,
  DEFAULT_EVALUATION_ENABLED,
  DEFAULT_SHOW_BEST_MOVE
} = EVALUATION_CONSTANTS;
