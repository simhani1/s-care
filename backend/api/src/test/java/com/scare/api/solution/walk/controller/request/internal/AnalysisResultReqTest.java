package com.scare.api.solution.walk.controller.request.internal;

import static org.assertj.core.api.Assertions.*;

import org.junit.jupiter.api.Test;

import com.fasterxml.jackson.databind.ObjectMapper;

class AnalysisResultReqTest {

	private final ObjectMapper mapper = new ObjectMapper();

	private AnalysisResultReq read(String json) throws Exception {
		return mapper.readValue(json, AnalysisResultReq.class);
	}

	@Test
	void 정상값과_힐링_구간_없음과_모르는_필드를_받는다() throws Exception {
		assertThat(read("{\"maxStress\":38.5,\"minStress\":22,\"healingStressAvg\":25.1,\"startIdx\":350,"
			+ "\"endIdx\":509,\"newField\":1}").maxStress()).isEqualTo(38.5);
		assertThatCode(() -> read("{\"maxStress\":20,\"minStress\":20,\"healingStressAvg\":0.0,\"startIdx\":0,"
			+ "\"endIdx\":0}")).doesNotThrowAnyException();
	}

	@Test
	void 범위를_벗어나거나_유한하지_않은_값은_거부한다() {
		String[] invalid = {
			"{\"maxStress\":-5,\"minStress\":10,\"healingStressAvg\":1,\"startIdx\":0,\"endIdx\":0}",
			"{\"maxStress\":61,\"minStress\":10,\"healingStressAvg\":1,\"startIdx\":0,\"endIdx\":0}",
			"{\"maxStress\":10,\"minStress\":20,\"healingStressAvg\":1,\"startIdx\":0,\"endIdx\":0}",
			"{\"maxStress\":30,\"minStress\":10,\"healingStressAvg\":\"NaN\",\"startIdx\":0,\"endIdx\":0}",
			"{\"maxStress\":30,\"minStress\":10,\"healingStressAvg\":\"Infinity\",\"startIdx\":0,\"endIdx\":0}",
			"{\"maxStress\":30,\"minStress\":10,\"healingStressAvg\":-1e300,\"startIdx\":0,\"endIdx\":0}",
			"{\"maxStress\":30,\"minStress\":10,\"healingStressAvg\":1,\"startIdx\":500,\"endIdx\":-3}",
			"{\"maxStress\":30,\"minStress\":10,\"healingStressAvg\":1,\"startIdx\":-1,\"endIdx\":3}",
			"{\"maxStress\":30,\"minStress\":10,\"healingStressAvg\":1,\"startIdx\":0}",
		};
		for (String json : invalid) {
			assertThatThrownBy(() -> read(json)).as(json).isInstanceOf(Exception.class);
		}
	}
}
