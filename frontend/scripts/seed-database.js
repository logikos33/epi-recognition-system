/**
 * Seed Database Script for EPI Recognition System
 *
 * This script populates the Supabase database with demo data for testing.
 * It creates:
 * - 3 example cameras
 * - 50+ detections with realistic EPI data
 * - Various timestamps from the last 24 hours
 * - Mix of compliant and non-compliant detections
 *
 * Usage:
 *   1. Make sure .env.local is configured with your Supabase credentials
 *   2. Run: node scripts/seed-database.js
 */

require('dotenv').config({ path: '.env.local' })
const { createClient } = require('@supabase/supabase-js')

// Check if environment variables are set
if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
  console.error('❌ Error: Supabase credentials not found in .env.local')
  console.error('Please set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY')
  process.exit(1)
}

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
)

// EPI types and their Portuguese labels
const EPI_TYPES = {
  helmet: { label: 'Capacete', required: true },
  vest: { label: 'Colete', required: true },
  gloves: { label: 'Luvas', required: true },
  goggles: { label: 'Óculos', required: false },
  mask: { label: 'Máscara', required: false },
  boots: { label: 'Botas', required: true }
}

// Camera data
const CAMERAS = [
  {
    name: 'Câmera Entrada Principal',
    location: 'Fábrica - Linha A',
    ip_address: '192.168.1.100',
    rtsp_username: 'admin',
    rtsp_password: 'password123',
    rtsp_port: 554,
    camera_brand: 'hikvision',
    is_active: true
  },
  {
    name: 'Câmera Linha de Produção',
    location: 'Fábrica - Linha B',
    ip_address: '192.168.1.101',
    rtsp_username: 'admin',
    rtsp_password: 'password123',
    rtsp_port: 554,
    camera_brand: 'dahua',
    is_active: true
  },
  {
    name: 'Câmera Depósito',
    location: 'Depósito Central',
    ip_address: '192.168.1.102',
    rtsp_username: 'admin',
    rtsp_password: 'password123',
    rtsp_port: 554,
    camera_brand: 'intelbras',
    is_active: true
  }
]

// Helper function to generate random EPI detection
function generateEPIsDetection() {
  const epis = {}
  const epiKeys = Object.keys(EPI_TYPES)

  // Randomly decide which EPIs are detected
  epiKeys.forEach(key => {
    // 70% chance of detecting each EPI
    epis[key] = {
      detected: Math.random() > 0.3,
      confidence: Math.random() * 0.3 + 0.7, // 70-100% confidence
      label: EPI_TYPES[key].label
    }
  })

  return epis
}

// Helper function to check compliance
function checkCompliance(epis) {
  const requiredEPIs = Object.entries(EPI_TYPES)
    .filter(([_, config]) => config.required)
    .map(([key, _]) => key)

  return requiredEPIs.every(key => epis[key]?.detected === true)
}

// Helper function to generate random timestamp within last 24 hours
function generateRandomTimestamp() {
  const now = new Date()
  const hoursAgo = Math.floor(Math.random() * 24)
  const minutesAgo = Math.floor(Math.random() * 60)
  const timestamp = new Date(now.getTime() - (hoursAgo * 60 + minutesAgo) * 60000)
  return timestamp.toISOString()
}

// Main seed function
async function seedDatabase() {
  console.log('🌱 Starting database seeding...\n')

  try {
    // Step 1: Clear existing data
    console.log('🗑️  Clearing existing data...')
    await supabase.from('detections').delete().neq('id', 0)
    await supabase.from('cameras').delete().neq('id', 0)
    console.log('✅ Existing data cleared\n')

    // Step 2: Create cameras
    console.log('📷 Creating cameras...')
    const { data: cameras, error: camerasError } = await supabase
      .from('cameras')
      .insert(CAMERAS)
      .select()

    if (camerasError) {
      console.error('❌ Error creating cameras:', camerasError)
      throw camerasError
    }

    console.log(`✅ Created ${cameras.length} cameras`)
    cameras.forEach(camera => {
      console.log(`   - ${camera.name} (${camera.location}) [ID: ${camera.id}]`)
    })
    console.log('')

    // Step 3: Generate detections
    console.log('🔍 Generating detections...')
    const detections = []
    const numDetections = 60 // Generate 60 detections

    for (let i = 0; i < numDetections; i++) {
      const camera = cameras[Math.floor(Math.random() * cameras.length)]
      const episDetected = generateEPIsDetection()
      const isCompliant = checkCompliance(episDetected)
      const confidence = Math.random() * 0.3 + 0.7 // 70-100%
      const personCount = Math.floor(Math.random() * 3) + 1 // 1-3 persons

      detections.push({
        camera_id: camera.id,
        timestamp: generateRandomTimestamp(),
        epis_detected: episDetected,
        confidence: confidence,
        is_compliant: isCompliant,
        person_count: personCount
      })
    }

    // Sort detections by timestamp (newest first)
    detections.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))

    // Insert detections in batches
    const batchSize = 50
    for (let i = 0; i < detections.length; i += batchSize) {
      const batch = detections.slice(i, i + batchSize)
      const { error: insertError } = await supabase
        .from('detections')
        .insert(batch)

      if (insertError) {
        console.error('❌ Error inserting detections:', insertError)
        throw insertError
      }
    }

    console.log(`✅ Created ${detections.length} detections`)

    // Calculate statistics
    const compliantCount = detections.filter(d => d.is_compliant).length
    const nonCompliantCount = detections.length - compliantCount
    const complianceRate = ((compliantCount / detections.length) * 100).toFixed(1)

    console.log(`   - Compliant: ${compliantCount} (${complianceRate}%)`)
    console.log(`   - Non-compliant: ${nonCompliantCount} (${(100 - complianceRate).toFixed(1)}%)`)
    console.log('')

    // Step 4: Verify data
    console.log('🔍 Verifying data...')
    const { count: camerasCount } = await supabase.from('cameras').select('*', { count: 'exact', head: true })
    const { count: detectionsCount } = await supabase.from('detections').select('*', { count: 'exact', head: true })

    console.log(`✅ Cameras in database: ${camerasCount}`)
    console.log(`✅ Detections in database: ${detectionsCount}`)
    console.log('')

    // Step 5: Show recent detections sample
    const { data: recentDetections } = await supabase
      .from('detections')
      .select(`
        *,
        camera:cameras(name)
      `)
      .order('timestamp', { ascending: false })
      .limit(5)

    console.log('📊 Sample of recent detections:')
    recentDetections.forEach(d => {
      const status = d.is_compliant ? '✅ Compliant' : '❌ Non-compliant'
      const time = new Date(d.timestamp).toLocaleString('pt-BR')
      console.log(`   [${status}] ${d.camera?.name || 'Unknown'} - ${time} - ${d.person_count} person(s)`)
    })

    console.log('\n🎉 Database seeded successfully!')
    console.log('\n📝 Next steps:')
    console.log('   1. Visit https://supabase.com → Table Editor to view your data')
    console.log('   2. Run the frontend: npm run dev')
    console.log('   3. Navigate to http://localhost:3000/dashboard')
    console.log('   4. You should see the demo data in the dashboard!')

  } catch (error) {
    console.error('\n❌ Error during seeding:', error)
    process.exit(1)
  }
}

// Run the seed function
seedDatabase()
