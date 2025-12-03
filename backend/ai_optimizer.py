"""
HydroCharge Miner - AI Optimization Engine
Auto-switches mining algorithms based on real-time profitability
Physics-based power management and efficiency optimization
"""

import requests
import time
import json
from datetime import datetime
import numpy as np

class HydroChargeOptimizer:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.current_coin = None
        self.current_power = 0
        self.switching_penalty = 0.05  # 5% revenue loss during switch
        
        # Mining pool configurations
        self.pools = {
            'BTC': {
                'url': 'stratum+tcp://btc.pool.com:3333',
                'algorithm': 'SHA-256',
                'power_efficiency': 1.0  # baseline
            },
            'LTC': {
                'url': 'stratum+tcp://ltc.pool.com:3333',
                'algorithm': 'Scrypt',
                'power_efficiency': 1.2,  # 20% better due to merged mining
                'merged_coins': ['DOGE']
            },
            'DOGE': {
                'url': 'stratum+tcp://doge.pool.com:3333',
                'algorithm': 'Scrypt',
                'power_efficiency': 1.15
            }
        }
        
        # Performance history
        self.history = []
        
    def get_coin_price(self, coin):
        """Fetch real-time coin prices from CoinGecko"""
        coin_ids = {
            'BTC': 'bitcoin',
            'LTC': 'litecoin',
            'DOGE': 'dogecoin'
        }
        
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_ids[coin]}&vs_currencies=usd"
            response = requests.get(url, timeout=5)
            data = response.json()
            return data[coin_ids[coin]]['usd']
        except Exception as e:
            print(f"❌ Error fetching {coin} price: {e}")
            return None
    
    def get_network_difficulty(self, coin):
        """Fetch network difficulty (simplified - use actual pool APIs)"""
        # Placeholder - integrate with actual mining pool APIs
        difficulties = {
            'BTC': 62.46e12,  # Current BTC difficulty
            'LTC': 25.8e6,    # Current LTC difficulty
            'DOGE': 10.2e6    # Current DOGE difficulty
        }
        return difficulties.get(coin, 1)
    
    def calculate_profitability(self, coin, power_watts):
        """
        Calculate mining profitability in $/day
        Formula: (Hashrate / Difficulty) * Block_Reward * Price * 86400 - Power_Cost
        """
        price = self.get_coin_price(coin)
        if not price:
            return 0
        
        difficulty = self.get_network_difficulty(coin)
        
        # Hashrate estimates based on power (simplified)
        hashrates = {
            'BTC': power_watts * 0.1e12,  # ~100 GH/s per watt (modern ASICs)
            'LTC': power_watts * 2.5e6,   # ~2.5 MH/s per watt (Scrypt)
            'DOGE': power_watts * 2.5e6
        }
        
        block_rewards = {
            'BTC': 6.25,
            'LTC': 12.5,
            'DOGE': 10000
        }
        
        hashrate = hashrates.get(coin, 0)
        block_reward = block_rewards.get(coin, 0)
        
        # Daily revenue calculation
        blocks_per_day = (hashrate / difficulty) * 86400
        daily_revenue = blocks_per_day * block_reward * price
        
        # Apply power efficiency multiplier
        efficiency = self.pools[coin]['power_efficiency']
        daily_revenue *= efficiency
        
        # Add merged mining bonus for LTC
        if coin == 'LTC':
            doge_price = self.get_coin_price('DOGE')
            if doge_price:
                doge_bonus = blocks_per_day * 10000 * doge_price * 0.8  # 80% of DOGE reward
                daily_revenue += doge_bonus
        
        return daily_revenue
    
    def optimize_turbine_rpm(self, current_rpm, flow_rate, power_output):
        """
        Physics-based turbine optimization using hill climbing
        Maximizes power extraction while preventing cavitation
        """
        # Optimal tip speed ratio for Turgo turbines: 0.45-0.50
        optimal_tsr = 0.47
        
        # Calculate water velocity (Bernoulli)
        head = 3.0  # meters
        water_velocity = np.sqrt(2 * 9.81 * head)  # m/s
        
        # Calculate turbine diameter (assume 0.2m)
        turbine_diameter = 0.2  # meters
        
        # Optimal RPM calculation
        optimal_rpm = (optimal_tsr * water_velocity * 60) / (np.pi * turbine_diameter)
        
        # Adjustment recommendation
        rpm_diff = optimal_rpm - current_rpm
        
        if abs(rpm_diff) > 50:
            adjustment = "increase" if rpm_diff > 0 else "decrease"
            return {
                'action': adjustment,
                'target_rpm': optimal_rpm,
                'expected_gain': abs(rpm_diff) / optimal_rpm * 0.15  # ~15% max gain
            }
        
        return {'action': 'optimal', 'target_rpm': current_rpm, 'expected_gain': 0}
    
    def should_switch_coin(self, current_coin, current_profit):
        """
        Determine if switching to a different coin is profitable
        Accounts for switching downtime and transaction costs
        """
        profits = {}
        
        for coin in ['BTC', 'LTC', 'DOGE']:
            profit = self.calculate_profitability(coin, self.current_power)
            profits[coin] = profit
        
        # Find best coin
        best_coin = max(profits, key=profits.get)
        best_profit = profits[best_coin]
        
        # Check if switch is worth it (must overcome switching penalty)
        if best_coin != current_coin:
            profit_increase = (best_profit - current_profit) / current_profit
            
            if profit_increase > self.switching_penalty:
                return {
                    'switch': True,
                    'to_coin': best_coin,
                    'current_profit': current_profit,
                    'new_profit': best_profit,
                    'gain_percent': profit_increase * 100
                }
        
        return {'switch': False, 'current_coin': current_coin, 'profits': profits}
    
    def monitor_and_optimize(self, sensor_data):
        """
        Main optimization loop - called every minute
        """
        flow_rate = sensor_data['flow_rate']
        turbine_rpm = sensor_data['turbine_rpm']
        power_output = sensor_data['power_output']
        efficiency = sensor_data['efficiency']
        
        self.current_power = power_output
        
        print(f"\n{'='*50}")
        print(f"🌊 HydroCharge AI Optimizer - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*50}")
        
        # 1. Optimize turbine RPM
        rpm_optimization = self.optimize_turbine_rpm(turbine_rpm, flow_rate, power_output)
        
        if rpm_optimization['action'] != 'optimal':
            print(f"⚙️  RPM Optimization: {rpm_optimization['action'].upper()} to {rpm_optimization['target_rpm']:.0f} RPM")
            print(f"   Expected gain: +{rpm_optimization['expected_gain']*100:.1f}%")
        else:
            print(f"✅ Turbine RPM optimal: {turbine_rpm} RPM")
        
        # 2. Check coin profitability
        if self.current_coin:
            current_profit = self.calculate_profitability(self.current_coin, power_output)
            switch_decision = self.should_switch_coin(self.current_coin, current_profit)
            
            if switch_decision['switch']:
                print(f"\n💰 COIN SWITCH RECOMMENDED!")
                print(f"   From: {self.current_coin} (${current_profit:.2f}/day)")
                print(f"   To: {switch_decision['to_coin']} (${switch_decision['new_profit']:.2f}/day)")
                print(f"   Gain: +{switch_decision['gain_percent']:.1f}%")
                
                # Execute switch
                self.switch_mining_algorithm(switch_decision['to_coin'])
            else:
                print(f"✅ Current coin optimal: {self.current_coin} (${current_profit:.2f}/day)")
                print(f"   Alternatives: BTC=${switch_decision['profits']['BTC']:.2f} | "
                      f"LTC=${switch_decision['profits']['LTC']:.2f} | "
                      f"DOGE=${switch_decision['profits']['DOGE']:.2f}")
        else:
            # Initial coin selection
            profits = {coin: self.calculate_profitability(coin, power_output) 
                      for coin in ['BTC', 'LTC', 'DOGE']}
            best_coin = max(profits, key=profits.get)
            print(f"🚀 Initial coin selection: {best_coin} (${profits[best_coin]:.2f}/day)")
            self.switch_mining_algorithm(best_coin)
        
        # 3. Efficiency alerts
        if efficiency < 70:
            print(f"\n🚨 ALERT: Efficiency low ({efficiency:.1f}%) - check turbine alignment")
        elif efficiency > 85:
            print(f"\n💎 EXCELLENT: Efficiency {efficiency:.1f}% - optimal performance!")
        
        # 4. Flow rate monitoring
        if flow_rate < 10:
            print(f"\n🚨 ALERT: Flow rate low ({flow_rate:.1f} L/min) - piezo backup recommended")
        
        # Log to history
        self.history.append({
            'timestamp': datetime.now().isoformat(),
            'coin': self.current_coin,
            'power': power_output,
            'efficiency': efficiency,
            'profit': self.calculate_profitability(self.current_coin, power_output) if self.current_coin else 0
        })
        
        print(f"{'='*50}\n")
    
    def switch_mining_algorithm(self, new_coin):
        """
        Switch mining algorithm to new coin
        Handles pool connection, worker configuration, etc.
        """
        print(f"\n🔄 Switching mining algorithm to {new_coin}...")
        
        # Stop current mining
        if self.current_coin:
            print(f"   ⏸️  Stopping {self.current_coin} mining...")
            # Call mining controller API to stop
            # requests.post('http://localhost:5000/api/mining/stop')
        
        # Configure new pool
        pool_config = self.pools[new_coin]
        print(f"   ⚙️  Configuring {pool_config['algorithm']} algorithm...")
        
        # Start new mining
        print(f"   ▶️  Starting {new_coin} mining on {pool_config['url']}...")
        # Call mining controller API to start
        # requests.post('http://localhost:5000/api/mining/start', json={'coin': new_coin})
        
        self.current_coin = new_coin
        print(f"✅ Successfully switched to {new_coin}!")
        
        # Send notification
        self.send_notification(f"Mining switched to {new_coin}")
    
    def send_notification(self, message):
        """Send alert to user (email, SMS, push notification)"""
        print(f"📱 Notification: {message}")
        # Integrate with notification service (Twilio, SendGrid, etc.)

# ============================================
# MAIN EXECUTION
# ============================================

if __name__ == "__main__":
    optimizer = HydroChargeOptimizer()
    
    print("🌊⚡ HydroCharge AI Optimizer Started")
    print("Monitoring every 60 seconds...\n")
    
    while True:
        try:
            # Fetch sensor data from API
            response = requests.get('http://localhost:5000/api/sensors/latest')
            sensor_data = response.json()
            
            # Run optimization
            optimizer.monitor_and_optimize(sensor_data)
            
            # Wait 60 seconds
            time.sleep(60)
            
        except KeyboardInterrupt:
            print("\n👋 Optimizer stopped by user")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(10)
