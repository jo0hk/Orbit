package com.example.myapplication

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.core.content.ContextCompat
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.GET
import retrofit2.http.Path
import kotlin.random.Random
import com.google.android.gms.location.LocationServices

// ── 데이터 클래스 ──────────────────────────────────────────────────────────────

data class MoodResponse(val mood: String)

data class ConversationResponseDto(
    val id: Long,
    val userId: Long,
    val speaker: String,
    val message: String,
    val createdAt: String
)

data class Mission(
    val title: String,
    val description: String
)

// ── Retrofit ──────────────────────────────────────────────────────────────────

interface OrbitApiService {
    @GET("mood")
    suspend fun getCurrentMood(): MoodResponse

    @GET("api/conversations/{userId}")
    suspend fun getConversations(@Path("userId") userId: Long): List<ConversationResponseDto>
}

object RetrofitClient {
    val apiService: OrbitApiService by lazy {
        Retrofit.Builder()
            .baseUrl("https://example.com/")
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(OrbitApiService::class.java)
    }
}

// ── 임시 미션 데이터 (AI 서버 연동 후 교체) ───────────────────────────────────

val missionList = listOf(
    Mission("아침 온기 나누기", "집에서 키링을 손바닥으로 3초간 가볍게 감싸 쥐기"),
    Mission("물 한 잔의 여유", "차나 물을 마시는 동안 키링을 옆에 두고 3분간 가만히 머물기"),
    Mission("산소 농도 체크", "키링 마이크 근처에서 천천히 깊은 호흡 소리 들려주기"),
    Mission("태양광 패널 정검", "어두운 방의 전등을 켜서 조도를 높여주기"),
    Mission("무중력 유영 연습", "키링을 손바닥 위에 올려고 가만히 10초간 바라보기"),
)

// ── MainActivity ──────────────────────────────────────────────────────────────

class MainActivity : ComponentActivity() {
    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val allGranted = permissions.entries.all { it.value }
        if (allGranted) Toast.makeText(this, "권한 승인 완료!", Toast.LENGTH_SHORT).show()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        checkBluetoothPermissions()
        setContent {
            Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                var showSplash by remember { mutableStateOf(true) }
                if (showSplash) {
                    SplashScreen(onFinished = { showSplash = false })
                } else {
                    OrbitMainScreen()
                }
            }
        }
    }

    private fun checkBluetoothPermissions() {
        val permissions = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            arrayOf(Manifest.permission.BLUETOOTH_SCAN, Manifest.permission.BLUETOOTH_CONNECT, Manifest.permission.ACCESS_FINE_LOCATION)
        } else {
            arrayOf(Manifest.permission.BLUETOOTH, Manifest.permission.BLUETOOTH_ADMIN, Manifest.permission.ACCESS_FINE_LOCATION)
        }
        val notGranted = permissions.filter { ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED }
        if (notGranted.isNotEmpty()) requestPermissionLauncher.launch(notGranted.toTypedArray())
    }
}

// ── 메인 화면 ─────────────────────────────────────────────────────────────────
@Composable
fun SplashScreen(onFinished: () -> Unit) {
    val stars = remember { List(150) { Pair(Offset(Random.nextFloat(), Random.nextFloat()), Random.nextFloat()) } }

    LaunchedEffect(Unit) {
        delay(2500L)
        onFinished()
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF04080F)),
        contentAlignment = Alignment.Center
    ) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            stars.forEach { (pos, sizeAlpha) ->
                drawCircle(
                    color = Color.White.copy(alpha = sizeAlpha * 0.6f + 0.15f),
                    radius = sizeAlpha * 2.5f + 0.8f,
                    center = Offset(pos.x * size.width, pos.y * size.height)
                )
            }
        }

        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Text(
                "ORBIT",
                color = Color(0xFF00E5FF),
                fontSize = 48.sp,
                fontWeight = FontWeight.Bold,
                fontFamily = FontFamily.Monospace,
                letterSpacing = 12.sp
            )
        }
    }
}
@Composable
fun OrbitMainScreen() {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()

    var currentMood by remember { mutableStateOf("calm") }
    var fuelLevel by remember { mutableFloatStateOf(0.15f) }
    var inputText by remember { mutableStateOf("") }
    var orbitResponse by remember { mutableStateOf("") }
    // GPS 이동거리 측정
    var totalDistance by remember { mutableFloatStateOf(0f) }
    var lastLocation by remember { mutableStateOf<android.location.Location?>(null) }
    val fusedLocationClient = remember { LocationServices.getFusedLocationProviderClient(context) }

    LaunchedEffect(Unit) {
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED) {
            val locationRequest = com.google.android.gms.location.LocationRequest.Builder(
                com.google.android.gms.location.Priority.PRIORITY_HIGH_ACCURACY, 5000L
            ).build()

            val locationCallback = object : com.google.android.gms.location.LocationCallback() {
                override fun onLocationResult(result: com.google.android.gms.location.LocationResult) {
                    result.lastLocation?.let { newLocation ->
                        lastLocation?.let { prev ->
                            val distance = prev.distanceTo(newLocation)
                            totalDistance += distance
                            // 100m 달성 시 AI 서버로 전송 (지금은 임시로 미션 성공 팝업)
                            if (totalDistance >= 100f) {
                                showMissionComplete = true
                                totalDistance = 0f // 초기화
                            }
                        }
                        lastLocation = newLocation
                    }
                }
            }
            fusedLocationClient.requestLocationUpdates(
                locationRequest,
                locationCallback,
                android.os.Looper.getMainLooper()
            )
        }
    }

    // 미션 상태
    var currentMissionIndex by remember { mutableIntStateOf(0) }
    val currentMission = missionList.getOrNull(currentMissionIndex)

    // 팝업 상태
    var showMissionComplete by remember { mutableStateOf(false) }
    var showMissionFail by remember { mutableStateOf(false) }
    var showCrisisPopup by remember { mutableStateOf(false) }
    var showEndingPopup by remember { mutableStateOf(false) }

    // 연료 애니메이션
    val animatedFuel by animateFloatAsState(
        targetValue = fuelLevel,
        animationSpec = tween(durationMillis = 1000),
        label = "fuel"
    )

    // 카메라 런처
    val cameraLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.TakePicturePreview()
    ) { bitmap ->
        if (bitmap != null) {
            // TODO: AI 서버로 사진 전송
            Toast.makeText(context, "사진 촬영 완료! AI 서버 연동 후 분석 예정", Toast.LENGTH_SHORT).show()
        }
    }

    LaunchedEffect(Unit) {
        while (true) {
            try {
                val response = RetrofitClient.apiService.getCurrentMood()
                currentMood = response.mood
            } catch (e: Exception) { }
            delay(1000L)
        }
    }

    val accentColor = when (currentMood) {
        "happy" -> Color(0xFFFFE156)
        "sad"   -> Color(0xFF7DBEFF)
        "angry" -> Color(0xFFFF6B5E)
        else    -> Color(0xFF00E5FF)
    }

    val bgColors = when (currentMood) {
        "happy" -> listOf(Color(0xFF1F1606), Color(0xFF0A0703))
        "sad"   -> listOf(Color(0xFF061226), Color(0xFF020812))
        "angry" -> listOf(Color(0xFF260707), Color(0xFF0E0303))
        else    -> listOf(Color(0xFF0C1422), Color(0xFF04080F))
    }

    val moodIcon = when (currentMood) {
        "happy" -> Icons.Filled.SentimentSatisfied
        "sad"   -> Icons.Filled.SentimentDissatisfied
        "angry" -> Icons.Filled.Warning
        else    -> Icons.Filled.Face
    }

    val orbitDialogue = when (currentMood) {
        "happy" -> "와! 대장님! 에너지가 넘쳐요!\n지구는 정말 아름답지 않나요?"
        "sad"   -> "치칙- 대장님... 삐- 너무 외로워요.\n저를 조금만 쓰다듬어 주실 수 있나요?"
        "angry" -> "삐빅- 대장님, 제 회로가 조금 뜨거워요.\n우주선에서 잠시 쉬어가는 건 어떨까요?"
        else    -> "치칙- 대장님, 시스템 안정적입니다.\n명령을 대기 중입니다. 오버."
    }

    val stars = remember { List(150) { Pair(Offset(Random.nextFloat(), Random.nextFloat()), Random.nextFloat()) } }

    // ── MISSION COMPLETE 팝업 ─────────────────────────────────────────────────
    if (showMissionComplete) {
        Dialog(onDismissRequest = {}) {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF0E1422)),
                border = BorderStroke(1.dp, Color(0xFFFFD27A))
            ) {
                Column(
                    modifier = Modifier.padding(28.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        "✦ MISSION COMPLETE ✦",
                        color = Color(0xFFFFD27A),
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        fontFamily = FontFamily.Monospace,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.fillMaxWidth()
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        "대장님, 임무를 성공적으로 완수했습니다.\n연료가 보충됩니다.",
                        color = Color(0xFFE6EDF6),
                        fontSize = 13.sp,
                        textAlign = TextAlign.Center,
                        lineHeight = 20.sp,
                        modifier = Modifier.fillMaxWidth()
                    )
                    Spacer(modifier = Modifier.height(24.dp))
                    Button(
                        onClick = {
                            showMissionComplete = false
                            fuelLevel = (fuelLevel + 0.03f).coerceAtMost(1.0f)
                            // 다음 미션으로 이동
                            if (currentMissionIndex < missionList.size - 1) {
                                currentMissionIndex++
                            }
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFFFD27A)),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Text("확인", color = Color.Black, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }

    // ── MISSION FAIL 팝업 ─────────────────────────────────────────────────────
    if (showMissionFail) {
        Dialog(onDismissRequest = {}) {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF0E1422)),
                border = BorderStroke(1.dp, Color(0xFF8A97AC))
            ) {
                Column(
                    modifier = Modifier.padding(28.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        "✦ MISSION FAIL ✦",
                        color = Color(0xFF8A97AC),
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        fontFamily = FontFamily.Monospace,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.fillMaxWidth()
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        "대장님, 이번 임무는 완수하지 못했습니다.\n다음 기회에 다시 도전해보세요.",
                        color = Color(0xFFE6EDF6),
                        fontSize = 13.sp,
                        textAlign = TextAlign.Center,
                        lineHeight = 20.sp,
                        modifier = Modifier.fillMaxWidth()
                    )
                    Spacer(modifier = Modifier.height(24.dp))
                    Button(
                        onClick = { showMissionFail = false },
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2A3A55)),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Text("확인", color = Color.White, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }

    // ── 위기발화 감지 팝업 ────────────────────────────────────────────────────
    if (showCrisisPopup) {
        Dialog(onDismissRequest = {}) {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF1A0A0A)),
                border = BorderStroke(1.dp, Color(0xFFFF6B5E))
            ) {
                Column(
                    modifier = Modifier.padding(28.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        "⚠ 긴급 교신",
                        color = Color(0xFFFF6B5E),
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        fontFamily = FontFamily.Monospace,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.fillMaxWidth()
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        "대장님, 지금 많이 힘드신가요?\n오빗이 곁에 있습니다.\n언제든지 도움을 요청하세요.",
                        color = Color(0xFFE6EDF6),
                        fontSize = 13.sp,
                        textAlign = TextAlign.Center,
                        lineHeight = 20.sp,
                        modifier = Modifier.fillMaxWidth()
                    )
                    Spacer(modifier = Modifier.height(24.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        OutlinedButton(
                            onClick = { showCrisisPopup = false },
                            border = BorderStroke(1.dp, Color(0xFFFF6B5E)),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Text("괜찮아요", color = Color(0xFFFF6B5E), fontWeight = FontWeight.Bold)
                        }
                        Button(
                            onClick = {
                                showCrisisPopup = false
                                // TODO: AI 서버에 위기 신호 전송
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFFF6B5E)),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Text("힘들어요", color = Color.White, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
        }
    }

    // ── 연료 100% 엔딩 팝업 ───────────────────────────────────────────────────
    LaunchedEffect(animatedFuel) {
        if (animatedFuel >= 1.0f) {
            showEndingPopup = true
        }
    }

    if (showEndingPopup) {
        Dialog(onDismissRequest = {}) {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF0A0F1E)),
                border = BorderStroke(1.dp, Color(0xFF00E5FF))
            ) {
                Column(
                    modifier = Modifier.padding(28.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        "🚀",
                        fontSize = 48.sp,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.fillMaxWidth()
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    Text(
                        "MISSION ACCOMPLISHED",
                        color = Color(0xFF00E5FF),
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        fontFamily = FontFamily.Monospace,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.fillMaxWidth()
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        "대장님, 드디어 고향 별로\n돌아갈 연료가 모두 모였습니다.\n오빗과 함께한 지구 탐사,\n정말 수고하셨습니다.",
                        color = Color(0xFFE6EDF6),
                        fontSize = 13.sp,
                        textAlign = TextAlign.Center,
                        lineHeight = 22.sp,
                        modifier = Modifier.fillMaxWidth()
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        "치칙- 귀환 항로 계산 완료.\n언제든 준비되시면 출발하겠습니다.\n오버.",
                        color = Color(0xFF00E5FF).copy(alpha = 0.7f),
                        fontSize = 12.sp,
                        textAlign = TextAlign.Center,
                        lineHeight = 20.sp,
                        fontFamily = FontFamily.Monospace,
                        modifier = Modifier.fillMaxWidth()
                    )
                    Spacer(modifier = Modifier.height(24.dp))
                    Button(
                        onClick = { showEndingPopup = false },
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF00E5FF)),
                        shape = RoundedCornerShape(12.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("고향으로 귀환하기", color = Color.Black, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }

    // ── 화면 렌더링 ───────────────────────────────────────────────────────────
    Box(modifier = Modifier.fillMaxSize()) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            drawRect(brush = Brush.verticalGradient(colors = bgColors))
            stars.forEach { (pos, sizeAlpha) ->
                drawCircle(
                    color = Color.White.copy(alpha = sizeAlpha * 0.6f + 0.15f),
                    radius = sizeAlpha * 2.5f + 0.8f,
                    center = Offset(pos.x * size.width, pos.y * size.height)
                )
            }
        }

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 20.dp, vertical = 24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // 상단 상태바
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(modifier = Modifier.size(8.dp).clip(CircleShape).background(accentColor))
                    Spacer(modifier = Modifier.size(8.dp))
                    Text("우주선 통신망 · 동기화 중", color = accentColor, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                }
                Text(
                    "지구 탐사 ${
                        run {
                            val prefs = LocalContext.current.getSharedPreferences("orbit_prefs", android.content.Context.MODE_PRIVATE)
                            val firstLaunch = prefs.getLong("first_launch", 0L).let {
                                if (it == 0L) {
                                    val now = System.currentTimeMillis()
                                    prefs.edit().putLong("first_launch", now).apply()
                                    now
                                } else it
                            }
                            val diff = System.currentTimeMillis() - firstLaunch
                            (diff / (1000 * 60 * 60 * 24)).toInt() + 1
                        }
                    }일차",
                    color = Color(0xFF8A97AC),
                    fontSize = 12.sp
                )
            }

            Spacer(modifier = Modifier.height(28.dp))

            // 연료 게이지
            Column(modifier = Modifier.fillMaxWidth()) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text("고향 별 복귀 연료", color = Color(0xFF8A97AC), fontSize = 12.sp)
                    Text("${(animatedFuel * 100).toInt()}%", color = Color(0xFFFFD27A), fontSize = 14.sp, fontWeight = FontWeight.Bold)
                }
                Spacer(modifier = Modifier.height(8.dp))
                LinearProgressIndicator(
                    progress = animatedFuel,
                    modifier = Modifier.fillMaxWidth().height(6.dp).clip(RoundedCornerShape(3.dp)),
                    color = Color(0xFFFFD27A),
                    trackColor = Color(0xFF1A2238)
                )
            }

            Spacer(modifier = Modifier.height(36.dp))

            // ORBIT 코어
            Box(contentAlignment = Alignment.Center) {
                Box(
                    modifier = Modifier.size(232.dp).clip(CircleShape).background(
                        brush = Brush.radialGradient(
                            colors = listOf(accentColor.copy(alpha = 0.3f), Color.Transparent)
                        )
                    )
                )
                Box(
                    modifier = Modifier
                        .size(200.dp)
                        .clip(CircleShape)
                        .background(Color(0xFF141C2E))
                        .border(1.5.dp, accentColor.copy(alpha = 0.6f), CircleShape),
                    contentAlignment = Alignment.Center
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(moodIcon, contentDescription = null, tint = accentColor, modifier = Modifier.size(72.dp))
                        Spacer(modifier = Modifier.height(10.dp))
                        Text("ORBIT", color = accentColor, fontSize = 16.sp, fontWeight = FontWeight.Bold, letterSpacing = 6.sp)
                    }
                }
            }

            Spacer(modifier = Modifier.height(28.dp))

            // 대사 카드
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF0E1422).copy(alpha = 0.85f)),
                shape = RoundedCornerShape(14.dp),
                border = BorderStroke(1.dp, accentColor.copy(alpha = 0.35f))
            ) {
                Column(
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 18.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = orbitDialogue,
                        color = Color(0xFFE6EDF6),
                        fontSize = 14.sp,
                        textAlign = TextAlign.Center,
                        lineHeight = 22.sp,
                        modifier = Modifier.fillMaxWidth()
                    )
                    if (orbitResponse.isNotEmpty()) {
                        Spacer(modifier = Modifier.height(12.dp))
                        Divider(color = accentColor.copy(alpha = 0.3f))
                        Spacer(modifier = Modifier.height(12.dp))
                        Text(
                            text = orbitResponse,
                            color = accentColor,
                            fontSize = 13.sp,
                            textAlign = TextAlign.Center,
                            lineHeight = 20.sp,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // 미션 위젯
            currentMission?.let { mission ->
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF0A1628).copy(alpha = 0.9f)),
                    shape = RoundedCornerShape(12.dp),
                    border = BorderStroke(1.dp, accentColor.copy(alpha = 0.25f))
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 16.dp, vertical = 12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Box(
                            modifier = Modifier
                                .size(6.dp)
                                .clip(CircleShape)
                                .background(accentColor)
                        )
                        Spacer(modifier = Modifier.width(10.dp))
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = "SYS_TASK · ${currentMissionIndex + 1}/${missionList.size}",
                                color = accentColor.copy(alpha = 0.6f),
                                fontSize = 10.sp,
                                fontFamily = FontFamily.Monospace,
                                letterSpacing = 1.sp
                            )
                            Spacer(modifier = Modifier.height(2.dp))
                            Text(
                                text = mission.title,
                                color = Color(0xFFE6EDF6),
                                fontSize = 13.sp,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = mission.description,
                                color = Color(0xFF8A97AC),
                                fontSize = 11.sp,
                                lineHeight = 16.sp
                            )
                        }
                    }
                }
            }

            // 테스트 버튼 (AI 연동 후 삭제)
            Spacer(modifier = Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                OutlinedButton(
                    onClick = { showMissionComplete = true },
                    border = BorderStroke(1.dp, Color(0xFFFFD27A)),
                    shape = RoundedCornerShape(8.dp),
                    contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp)
                ) {
                    Text("미션성공 테스트", color = Color(0xFFFFD27A), fontSize = 10.sp)
                }
                OutlinedButton(
                    onClick = { showMissionFail = true },
                    border = BorderStroke(1.dp, Color(0xFF8A97AC)),
                    shape = RoundedCornerShape(8.dp),
                    contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp)
                ) {
                    Text("미션실패 테스트", color = Color(0xFF8A97AC), fontSize = 10.sp)
                }
                OutlinedButton(
                    onClick = { showCrisisPopup = true },
                    border = BorderStroke(1.dp, Color(0xFFFF6B5E)),
                    shape = RoundedCornerShape(8.dp),
                    contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp)
                ) {
                    Text("위기발화 테스트", color = Color(0xFFFF6B5E), fontSize = 10.sp)
                }
            }

            Spacer(modifier = Modifier.weight(1f))

            // 하단 입력창 + 카메라 버튼
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                IconButton(
                    onClick = { cameraLauncher.launch(null) },
                    modifier = Modifier
                        .size(52.dp)
                        .background(Color(0xFF1A2238).copy(alpha = 0.9f), CircleShape)
                        .border(1.dp, accentColor.copy(alpha = 0.4f), CircleShape)
                ) {
                    Icon(
                        Icons.Filled.CameraAlt,
                        contentDescription = "카메라",
                        tint = Color.White,
                        modifier = Modifier.size(24.dp)
                    )
                }

                OutlinedTextField(
                    value = inputText,
                    onValueChange = { inputText = it },
                    placeholder = {
                        Text("오빗에게 교신하기...", color = Color(0xFF8A97AC), fontSize = 13.sp)
                    },
                    modifier = Modifier
                        .weight(1f)
                        .height(52.dp),
                    shape = RoundedCornerShape(26.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = accentColor.copy(alpha = 0.6f),
                        unfocusedBorderColor = Color(0xFF2A3A55),
                        focusedTextColor = Color.White,
                        unfocusedTextColor = Color.White,
                        cursorColor = accentColor,
                        focusedContainerColor = Color(0xFF1A2238).copy(alpha = 0.9f),
                        unfocusedContainerColor = Color(0xFF1A2238).copy(alpha = 0.9f),
                    ),
                    singleLine = true,
                    trailingIcon = {
                        IconButton(
                            onClick = {
                                if (inputText.isNotBlank()) {
                                    coroutineScope.launch {
                                        try {
                                            // TODO: AI 서버 연동 시 여기서 inputText를 AI 서버로 전송
                                            orbitResponse = "AI 서버 연동 후 응답이 여기 표시됩니다."
                                            inputText = ""
                                        } catch (e: Exception) {
                                            orbitResponse = "교신 실패. 다시 시도하세요."
                                        }
                                    }
                                }
                            }
                        ) {
                            Icon(
                                Icons.Filled.Send,
                                contentDescription = "전송",
                                tint = accentColor,
                                modifier = Modifier.size(20.dp)
                            )
                        }
                    }
                )
            }
        }
    }
}