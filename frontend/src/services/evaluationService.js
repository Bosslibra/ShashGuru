import axios from 'axios'
import { DEFAULT_DEPTH, DEFAULT_SHOW_LINES } from '@/constants/evaluation.js'

export class EvaluationService {
  // Cache for memoizing evaluation results
  static evaluationCache = new Map()
  
  // Cache expiry time (5 minutes)
  static CACHE_EXPIRY = 5 * 60 * 1000
  
  static async fetchEvaluation(fen, depth = DEFAULT_DEPTH, lines = DEFAULT_SHOW_LINES) {
    if (!fen) {
      return null
    }
    
    // Create cache key from parameters
    const cacheKey = `${fen}_${depth}_${lines}`
    
    // Check if we have a cached result
    if (this.evaluationCache.has(cacheKey)) {
      const cached = this.evaluationCache.get(cacheKey)
      const now = Date.now()
      
      // Return cached result if it's still valid
      if (now - cached.timestamp < this.CACHE_EXPIRY) {
        return cached.result
      } else {
        // Remove expired cache entry
        this.evaluationCache.delete(cacheKey)
      }
    }
    
    try {
      // Determine whose turn it is from the FEN
      const fenParts = fen.split(' ')
      const isWhiteToMove = fenParts[1] === 'w'
      
      const server_url = import.meta.env.BASE_URL + 'backend'
      const response = await axios.post(`${server_url}/evaluation`, {
        fen: fen,
        depth: depth,
        lines: lines
      })
      
      if (response.data && response.data.evaluation) {
        // Store both the evaluation and the side info for proper interpretation
        const result = {
          ...response.data.evaluation,
          sideToMove: isWhiteToMove ? 'white' : 'black',
          fen: fen
        }
        
        // Cache the result
        this.evaluationCache.set(cacheKey, {
          result: result,
          timestamp: Date.now()
        })
        
        return result
      }
    } catch (error) {
      console.error('Error fetching evaluation:', error)
      throw error
    }
    
    return null
  }
  
  // Method to clear the cache if needed
  static clearCache() {
    this.evaluationCache.clear()
  }
  
  // Method to get cache statistics
  static getCacheStats() {
    return {
      size: this.evaluationCache.size,
      entries: Array.from(this.evaluationCache.keys())
    }
  }
}
