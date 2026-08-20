package com.bdlh.touchstone.data;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;

@SpringBootTest
@EnabledIfEnvironmentVariable(named = "TOUCHSTONE_INTEGRATION_TEST", matches = "true")
class FlywayMigrationTest {
    @Autowired JdbcTemplate jdbc;

    @Test
    void migrationsCreateAndSeedTheFixedCatalog() {
        Integer cases = jdbc.queryForObject(
                "SELECT count(*) FROM touchstone.case_definitions", Integer.class);
        Integer snapshots = jdbc.queryForObject(
                "SELECT count(*) FROM touchstone.data_snapshots", Integer.class);

        assertThat(cases).isEqualTo(18);
        assertThat(snapshots).isEqualTo(18);
    }
}
