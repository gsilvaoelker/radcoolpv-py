%
% Atmospheric transmittance and energy balance for cooling PV cells.
% Author: Gerardo Silva-Oelker
% Last update: Oct. 5, 2023
% 
% Code version: 11
% New code version able to read data from FreeForm calculations (work in
% progress).
% 
% Validations:
% 1) Fig. 2 Perrakis et al., 2020. Use parameter runTest = yes to run this
% case.
% 2) 

%%
clear all; clf; clc; tic;

% --- comparison driver: run from the repo root so relative data paths work ---
projectRoot = '/Users/gerardosilvaoelker/Desktop/Research Projects/radCoolPV';
cd(projectRoot);
addpath(projectRoot);
addpath(fullfile(projectRoot, 'settings'));
addpath(fullfile(projectRoot, 'permittivityDataBase'));
comparisonOut = fullfile(projectRoot, 'radcoolpv-py', 'comparison', 'matlab_out');

% Run some useful things:
% Load constants (materials DB not needed in free-form mode).
run(fullfile(projectRoot, 'settings', 'constants.m'))


% Create a results folder (fixed, inside the comparison directory).
resultsFolderName = comparisonOut;
mkdir([resultsFolderName]);

%% Main parameters.

% In case of running a test with validation is needed:
% Validation considers comparisons with Perrakis et al., 2020, OPEX paper.
% First test: Fig. 2
runTest = 'no'; % yes or no.

% Second test: Fig. 
runTest2 = 'no'; % yes or no.


% Silicon layer thicknes in um.
% This needs to be coincident with mainMatlabS4 structure.
thickSi = 250;

%Voltage array.
%V = [0.7] %This needs to be a variable
voltArray = linspace(0.1,0.8,100);

% Ambient temperature in K.
tempAmb   = 298;
% Convective coefficient in W/m2-C.
convCoeff = 12;

% Running a test/validation case.
if isequal(runTest, 'yes')
    % This overwrites values of temperature and heat transfer above.
    tempAmb   = 300;
    convCoeff = 0;  
    angleDef = 'hemisph';  
    
elseif isequal(runTest2, 'yes')
    % This overwrites values of temperature and heat transfer above.
    tempAmb   = 298;
    convCoeff = 13.7;  % W/m2 K
    angleDef = 'hemisph'; 
    
else
    %
    % Here one can choose between normal or hemispherical calculation.
    % Chose normal or hemispherical calculations.
    %
    angleDef = 'normal';
    %angleDef = 'hemisph';
    
end    

% Theta and lambda arrays. These array must match the number of columns for
% the emittance arrays, i.e, the number of angles of incidence.
if isequal(angleDef, 'normal')
    thetaDeg            = [0];
elseif isequal(angleDef, 'hemisph')
    thetaDeg            = [0 5 10 15 20 25 30 35 40 45 50 55 60 65 70 75 80 85];
end

% Array size and radians.
nTheta              = length(thetaDeg);
thetaIncidentArray  = thetaDeg*pi/180;

% !!!!!!!!!!!!!!!
% !!!!Warning!!!!
% !!!!!!!!!!!!!!!
% This needs to match the wavelength window and number of
% points used in the MatlabS4 simulation. See .log file for info.
lambdaInitial = 0.3; % Smallest wavelength in um.
lambdaFinal   = 30.0;% Largest wavelength in um.
nLambda       = 1000;

runFF_data = 'yes'; % yes or no.
if isequal(runFF_data,'yes')
    
    %%%%%%
    % Add the name of the results file in the freeFormData folder.
    %%%%%%
    %dataFF_nameFile = "NIL_tT50um_2x2um_R1_4_opt_2um_Res.txt";
    %dataFF_nameFile = "NIL_tT50um_P1024_R256_opt_1um_AO_Res.txt";
    %dataFF_nameFile = "NIL_tT50um_P2048_R512_opt_2um_AO_Res.txt";
    dataFF_nameFile = "NIL_tT50um_tT50um_2x2um_R1_4_opt_1um_Res.txt";
    dataFF_table    = readtable(strcat("freeFormData/",dataFF_nameFile));
    dataFF          = table2array(dataFF_table);
    dataFF_lambda   = dataFF(:,1);
    dataFF_totRef   = dataFF(:,2);
    dataFF_totAbs   = dataFF(:,3);
    dataFF_SiAbs    = dataFF(:,7);

    % Wavelengths arrays.
    lambdaInitial = dataFF_lambda(1);
    lambdaFinal   = dataFF_lambda(length(dataFF_lambda));

end



if isequal(runTest2, 'yes')
   % This is needed to concatenate data taken from paper's Figs.
  lambdaInitial = 2.31; % Smallest wavelength in um.  
end

% wavelength array in um.
lambdaArray     = linspace(lambdaInitial, lambdaFinal, nLambda);
lambdaDelta     = lambdaArray(2) - lambdaArray(1);


if isequal(runFF_data,'yes')

    totRef = interp1(dataFF_lambda, dataFF_totRef, lambdaArray);
    totAbs = interp1(dataFF_lambda, dataFF_totAbs, lambdaArray);
    SiAbs  = interp1(dataFF_lambda, dataFF_SiAbs, lambdaArray);

end



%% Data of directional emittances of the thermal emitter.

% Running a test/validation case.
if isequal(runTest, 'yes')
    % Valdiation plots for Quartz (SiO2 properties).
    % This validation needs to be run using a wavelength range 4-30 um
    filePath = '/Users/gerardosilvaoelker/Dropbox/codes/matlab/radiativeCoolingForSolarCells-LPR19-08/radCoolPV-Matlab/radCoolPV_v06/literatureData/quartzValidations-4-30um';

elseif isequal(runTest2, 'yes')
    % Valdiation plots for Quartz (SiO2 properties).
    % This validation needs to be run using a wavelength range 2.31-30 um
    % and Si thickness of 250 um.
    filePath = '/Users/gerardosilvaoelker/Dropbox/codes/matlab/radiativeCoolingForSolarCells-LPR19-08/radCoolPV-Matlab/radCoolPV_v06/literatureData/quartzValidations-2.31-30um';
else
    
    %
    % This path changes according to the cases one'd like to run.
    %
    filePath = '/Users/gerardosilvaoelker/Dropbox/codes/matlab/radiativeCoolingForSolarCells-LPR19-08/radCoolPV-Matlab/radCoolPV_v11/results_18-May-2022_10:18:43';

end



% Choose the type of calculation: normal or hemisph.
if isequal(angleDef, 'normal')

    if isequal(runFF_data,'yes')
    ref            = totRef;
    refNorm        = totRef;
    tran           = 1.0 - totAbs - totRef;
    emitSpectral   = totAbs;
    emissNorm      = totAbs;
    absSilicon     = SiAbs;
    absSiliconNorm = SiAbs;


    % Run atmospheric data interpolated for the used wavelengths.
    run 'atmosphericData.m';
    emisAtm      = 1.0 - atmTransInterp;

    elseif isequal(runFF_data,'no')
    % Read normal data from MatlabS4 output.
    [ref,tran, emitSpectral, absSilicon, emisAtm] = normalPropsFunc(filePath,nLambda);

    end
    
    
    % For normal calculations.
    for index = 1:nLambda
        emittSpecTimesEmitAtm(index) = emitSpectral(index)*emisAtm(index);
        %emitSpectral(index) = emiss(index);
    end
    
elseif isequal(angleDef, 'hemisph')
    % Read hemispherical data from MatlabS4 output.
    [ref,tran, emitSpectral, absSilicon, emittSpecTimesEmitAtm, emisAtm]...
        = hemisphPropsFunc(filePath,thetaDeg,nLambda);
    
    % Read normal properties required to calculate non-thermal radiation
    % since cell absortion for normal incidende is needed.
     [refNorm,tranNorm, emissNorm, absSiliconNorm, emittSpecTimesEmitAtmNorm, emisAtmNorm] ...
    = hemisphPropsFunc(filePath, 0,nLambda);
    
    % For hemispherical calculations.
    %for index = 1:nLambda
    %    emitSpectral(index) = emiss(index);
    %end
    
    if isequal(runTest2, 'yes')
        
        % This part is needed since part of the absorption is taken from
        % paper's Figs.
        getValidationPVAbs = dlmread('literatureData/pvCellAbsorptionEncapsulated-Perrakis2020-OPEX.dat');
        xAbsPV = getValidationPVAbs(:,1);
        yAbsPV = getValidationPVAbs(:,2);
        
        
        % Need to concatenate files.
        lambdaCat = cat(1, xAbsPV, lambdaArray');
        emisCat   = cat(1, yAbsPV, emitSpectral');
        
        lambdaArray     = linspace(0.3, lambdaFinal, nLambda);
        lambdaDelta     = lambdaArray(2) - lambdaArray(1);        
        emitSpectral    = [];
        
        emitSpectral = interp1(lambdaCat,emisCat,lambdaArray);
        %emiss = emitSpectral;
    end
end

%% Ideal radiative cooler emittance (atmospheric window).
% it includes:
% -ideal UV reflection in 0.3-0.375 um
% -ideal sub-bandgap reflection in 1.1-4.0 um
% -ideal emissivity in 4-33 um.

% UV reflectivity
% for index = 1:length(lambdaArray)
%     if lambdaArray(index) > 4.0 && lambdaArray(index) < 33
%         emitIdealRadCool(index) = 1;
%     else
%         emitIdealRadCool(index) = 0;
%     end
% end

% Sub bandgap reflectivity


% IR emissivity
for index = 1:length(lambdaArray)
    if lambdaArray(index) > 4.0 && lambdaArray(index) < 33
        emitIdealRadCool(index) = 1;
    else
        emitIdealRadCool(index) = 0;
    end
end
% Emissivity of the surface
emitSurfaceRadCool = emitIdealRadCool;

% If using an ideal emitter, emitSpectral has to be overwritten.
%emitSpectral = emitSurfaceRadCool;

%%  Calculation of the absorbed, convection, and atmospheric power.

% pi is because of the integration of the solid angle times cos.
atmPower = pi*RadTermFunc(lambdaArray, emittSpecTimesEmitAtm, tempAmb); % in W/m2.

% Loop to plot as a function of emitter temperature.
nTemp = 50;
initialTempEmitter = tempAmb;
for index = 1:nTemp
    % Emitter temperature for convection plot.
    %T_emitt(ind)        = 308 - (ind - 1);
    
    % Emitter temperature.
    emitTemp(index)            = initialTempEmitter + (index - 1);
    
    % Power due convection and conduction.
    convPowerTempArray(index)  = convCoeff*(emitTemp(index) - tempAmb);
    
    % Power radiated by the emitter (cooler). 
    radPowerForTempArray(index) = pi*RadTermFunc(lambdaArray, emitSpectral, emitTemp(index));
end

% Array point corresponding to ambient temperature.
% Consdering 1/2 since the temperatura varies every 1K.
ambTempIndex = find(emitTemp > tempAmb - 1/2 & emitTemp < tempAmb + 1/2);
emitTemp(ambTempIndex);

% =========================================================================
% EMITTER'S TEMPERATURE
% =========================================================================
% Emitt temperature at equilibrium temperature.
% The equilibrium temperature is obtained from the energy balance below.
% !!!!!!!!!!!!!!!
% !!!!Warning!!!!
% !!!!!!!!!!!!!!!
% This is a two steps process. Once temperature is calculated below it has
% to be replaced here to adjuts all the terms that depend on temperature.
emitTempLook = 319; %************************** Here!  T paper = 326
emitTempIndex = find(emitTemp > emitTempLook - 1/2 & emitTemp < emitTempLook + 1/2);
emitTemp(emitTempIndex);

%% Solar spectrum,  solar irradiance, and atmospheric properties.
%  AM1.5 Global spectrum.
run 'solarSpectrum.m'

% Additional output for cheking purposes.
disp('Solar power in W/m2 =')
disp(solarPower) % Solar power absorbed by the structure.

disp('Solar power AM1.5G in W/m2 =')
disp(solarPowerAM15) % ~1000 W/m2

% Running a test/validation case.
if isequal(runTest, 'yes')
    % This overwrites solarPowerAbove. Only for validation purposes.
    solarPower = 620; %W/m2
end

% Run atmospheric data interpolated for the used wavelengths.
%run 'atmosphericData.m';

%% PV calculations.

% PV cell properties.
% Bandgap in um, indenpendent of temperature.
% lamEg   = 1.107;

% Temperature dependence silicon bangap.
% source: https://ecee.colorado.edu/
alphaBandGap = 4.73e-4; % in eV/K.
betaBandGap  = 636; % in K.
bandGap0     = 1.166; % in eV.

bandGapTempElecVolts = bandGap0 - alphaBandGap*emitTemp.^2/(emitTemp + betaBandGap);
lamEg = HPLANCK*CLIGHT/(bandGapTempElecVolts*ECHARGE)/MICRON; % in um.

% Running a test/validation case.
if isequal(runTest, 'yes')
    % No PV calculations.
    lamEgIndex = 2;    
else
    
    % Array point corresponding to the lam_eg.
    lamEgIndex = find(lambdaArray > lamEg - lambdaDelta/2 & lambdaArray < lamEg + lambdaDelta/2);
end

% Intrinsic carrrier concentation of silicon.
% source: Accurate measurement of the silicon intrinsic carrier density.
% from 78 K to 340 K.
nivsT_T  = [256.5 270.6 281 300 319.5 340.5];
nivsT_ni = [1.45e8 6.7e8 1.79e9 9.7e9 4.51e10 1.89e11];

% Auger recombination of undoped silicon.
% source: Temperature dependence of Auger recombination coefficient.
AaugervsT_T = [195 252 294 333 372];
AaugervsT_A = [3.03e-31 3.51e-31 3.88e-31 4.15e-31 4.55e-31];

% PV cell absorption calculated using mainMatlabS4.
if isequal(runTest, 'yes')
    getValidationPVAbs = dlmread('literatureData/pvCellAbsorptionEncapsulated-Perrakis2020-OPEX.dat');
    xAbsPV = getValidationPVAbs(:,1);
    yAbsPV = getValidationPVAbs(:,2);
    
 elseif isequal(runTest2, 'yes')
     getValidationPVAbs = dlmread('literatureData/pvCellAbsorptionEncapsulated-Perrakis2020-OPEX.dat');
     xAbsPV = getValidationPVAbs(:,1);
     yAbsPV = getValidationPVAbs(:,2);    
    
else
    xAbsPV     = lambdaArray;
    yAbsPV     = absSilicon;
    yAbsPVNorm = absSiliconNorm;    
end

% Interpolated PV absorption. It is used only up to \lambda_g
absPVInterp = interp1(xAbsPV,yAbsPV,lambdaArray);
absPVInterp(isnan(absPVInterp)) = 0; % This puts 0 instead of NaN.

% Read and intepolate IQE.
% Source: Industrally feasible >19% efficiency IBC cells for pilot line
% processing by Castaño et al., 2011.
getIQE = dlmread('siliconIQE.txt');
IQEx = getIQE(:,1);
IQEy = getIQE(:,2);

IQEinterp = interp1(IQEx,IQEy,lambdaArray);
IQEinterp(isnan(IQEinterp)) = 0; % This puts 0 instead of NaN.

% Tests consider IQE = 1. Assumption in Perrakis et al., paper.
if isequal(runTest, 'yes')
    
    shortCircCurrentSpectral = absPVInterp(1:1:lamEgIndex).*...
        photonFluxSunSpectral(1:1:lamEgIndex); % This is actually zero.
    
elseif isequal(runTest2, 'yes')
    
    shortCircCurrentSpectral = absPVInterp(1:1:lamEgIndex).*...
        photonFluxSunSpectral(1:1:lamEgIndex);
    
else
    shortCircCurrentSpectral = IQEinterp(1:1:lamEgIndex).*...
        absPVInterp(1:1:lamEgIndex).*photonFluxSunSpectral(1:1:lamEgIndex);
 
    % IQE = 1.
    %shortCircCurrentSpectral = absPVInterp(1:1:lamEgIndex).*photonFluxSunSpectral(1:1:lamEgIndex);    
    
end

% Short-circuit current density in A/m2.
shortCircCurrent      = ECHARGE*trapz(lambdaArray(1:1:lamEgIndex),shortCircCurrentSpectral)*MICRON;
shortCircCurrentmAcm2 = shortCircCurrent*MILI/M2TOCM2;

disp('Short circuit current A/m2 =')
disp(shortCircCurrent)
%disp('Short circuit current mA/cm2 =')
%disp(shortCircCurrentmAcm2)

% Auger recombination rate; voltage and temperature dependent. 
% The colon is because of the voltage.
for index = 1:length(emitTemp)
    
    % niAtEmitTemp    = interp1(nivsT_T, nivsT_ni, emitTemp(index))/(1/MTOCM)^3; %cm-3 -> m-3.
    % Using a fitting curve from the same paper.
    niAtEmitTemp    = 5.29e19*(emitTemp(index)/300)^(2.54)*exp(-6726/emitTemp(index))/(1/MTOCM)^3; %cm-3 -> m-3.
    augerAtEmitTemp = interp1(AaugervsT_T, AaugervsT_A, emitTemp(index))*(1/MTOCM)^6; % cm6/s -> m6/s.
    
    % Current density due to Auger.
    % Units: C* m6/s * m-9 * m --> C/m2-s.
    % Auger model can be improved since there are newer papaer with better
    % models.
    augerCurrentDens(index,:) = ECHARGE*2*augerAtEmitTemp*niAtEmitTemp^3*thickSi*MICRON*...
        exp(3*ECHARGE*voltArray./(2*KBOLTZ*emitTemp(index)));
    
    for index2 = 1:lamEgIndex
        % Blackbody photon flux at the emitter temperature. Units:
        % photons/s x 1/m^2 x 1/mum --> photons/s x 1/mum^3.
        photonFluxBlackbody = (2*pi*CLIGHT*MTOMICRON/lambdaArray(index2)^4)*... % Units.
            1/(exp(HPLANCK*CLIGHT/(lambdaArray(index2)*MICRON*KBOLTZ*emitTemp(index)))- 1); % Unitless.
        
        % Spectral irradiance. Units: J/s x 1/mum^3.
        irradSpectral = photonFluxBlackbody*HPLANCK*CLIGHT*MTOMICRON/(lambdaArray(index2)*pi);
        
        % Spectral saturation current.
        currentSatSpectral(index,index2) = IQEinterp(index2).*absPVInterp(index2)*photonFluxBlackbody;
        
        % Non-thermal radiation (luminesence) emitted by the cell.         
        nonThermalPowerSpectral(index, index2) = IQEinterp(index2).*absSiliconNorm(index2)*irradSpectral;
        
    end
    
    % Saturation current. Units: C/m2-s.
    currentSat(index) = ECHARGE*trapz(lambdaArray(1:1:lamEgIndex),...
        currentSatSpectral(index,:))/MICRON2TOM2;
    
            
    % =====================================================================
    % Current density. The colon is because of the voltage.
    % =====================================================================
    
    
    if isequal(runTest2, 'yes')
        
        %Source: units
        seriesRes = 0.0;%/M2TOCM2; % Ohm cm2 -> Ohm m2
        % Source: units
        shuntRes  = 1000; % Ohm cm2 -> Ohm m2
        
    else
        
        %Source: units
        seriesRes = 0.00011;%/M2TOCM2; % Ohm cm2 -> Ohm m2
        % Source: units
        shuntRes  = 0.1; % Ohm cm2 -> Ohm m2
        
    end
    
    
    %currentDens(index,:) =   currentSat(index)*...
    %    (exp(ECHARGE*voltArray./(KBOLTZ*emitTemp(index))) - 1) + ...
    %    augerCurrentDens(index,:) - shortCircCurrent;
       
    % When series resistance is added it is necessary to solve a non-linear
    % equation; that's why there is an fsolve.
    Id0 = shortCircCurrent;
    for indexVolt = 1:length(voltArray)
        
%         fcurrent = @(Id)  -Id + currentSat(index)*...
%             (exp(ECHARGE*(voltArray(indexVolt) - Id*seriesRes)./(KBOLTZ*emitTemp(index))) - 1) + ...
%             augerCurrentDens(index,indexVolt) - shortCircCurrent;
        
           fcurrent = @(Id)  -Id + ...
               (voltArray(indexVolt) - Id*seriesRes)/shuntRes +...
                currentSat(index)*...
            (exp(ECHARGE*(voltArray(indexVolt) - Id*seriesRes)./(KBOLTZ*emitTemp(index))) - 1) + ...
            augerCurrentDens(index,indexVolt) - shortCircCurrent;
        
        
        optionsFsolve = optimoptions('fsolve','Display','none');
        Id  = fsolve(fcurrent,Id0, optionsFsolve);
        currentDens(index,indexVolt) =  Id;
        Id0 = Id; % New starting point for fsolve iterations.
        
    end
    
    % Non-thermal radiation emitted by the PV cell. Units: W/m2.
    % !!!!!!!!!!!!!!!
    % !!!!Warning!!!!
    % !!!!!!!!!!!!!!!
    % This is also a two step process. Therefore,
    % Vmpp needs to be calculated previously.
    
    Vmpp = 0.6586; %***********
    
    % nonThermalPowerSpectral Units: J/s x 1/mu^2 x 1/mu.
    nonThermalPower(index) = pi*trapz(lambdaArray(1:1:lamEgIndex),...
        nonThermalPowerSpectral(index,:))*... % J/s 1/m2 --> W/m2.
        exp((ECHARGE*Vmpp)/(KBOLTZ*emitTemp(index)) )/MICRON2TOM2;
      
end % Here ends the temperature loop.

% Calculation of maximum power point at ambient temperature.
for index = 1:length(voltArray)
    cellPowerAtAmbTemp(index) = -currentDens(ambTempIndex, index).*voltArray(index);
end
maxPowerPointAtAmbTemp = max(cellPowerAtAmbTemp);
disp('MPP at ambient temperature (W/m2) =')
disp(maxPowerPointAtAmbTemp)

% Calculation of maximum power point at emitter's (equil.) temperature.
for index = 1:length(voltArray)
    cellPowerAtEmitTemp(index) = -currentDens(emitTempIndex, index).*voltArray(index);
end
[maxPowerPointAtEmitTemp, maxPowerPointAtEmitTempIndex]= max(cellPowerAtEmitTemp);
disp('MPP at emitter temperature (W/m2) =')
disp(maxPowerPointAtEmitTemp)

voltageMpp = voltArray(maxPowerPointAtEmitTempIndex);
disp('Voltage at the MPP (V)')
disp(voltageMpp )
currentMPP = currentDens(emitTempIndex,maxPowerPointAtEmitTempIndex);
disp('Current at the MPP (A/m2) =')
disp(-currentMPP)


if isequal(runTest, 'yes')
    % no PV calculations.
    openCircuitVoltAtAmbTemp = 0;
    openCircuitVoltAtEmitTemp = 0;
else
    % Open circuit voltages.
    openCircuitVoltAtAmbTemp  = voltArray(find(-currentDens(ambTempIndex,:)  < 0, 1, 'first') - 1);
    openCircuitVoltAtEmitTemp = voltArray(find(-currentDens(emitTempIndex,:) < 0, 1, 'first') - 1);
end

disp('Voc (V) =')
disp(openCircuitVoltAtEmitTemp)


% Calculation of fill factor at ambient temperature.
ambTempFF  = maxPowerPointAtAmbTemp/(shortCircCurrent*openCircuitVoltAtAmbTemp);
disp('FF at ambient temperature (W/m2) =')
disp(ambTempFF)
% Calculation of fill factor at emitter's (equil.) temperature.
emitTempFF = maxPowerPointAtEmitTemp/(shortCircCurrent*openCircuitVoltAtEmitTemp);
disp('FF at emitter temperature (W/m2) =')
disp(emitTempFF)

%
% Temperature dependence maximum electrical power.
%
for index2 = 1:length(emitTemp)
    for index = 1:length(voltArray)
        cellPower(index,index2) = -currentDens(index2, index).*voltArray(index);
    end
    maxPowerPoint(index2) = max(cellPower(:,index2));
end

%maxPowerPointTest
% Cell maximum power as a function of temperature.
%maxPowerPoint = max(cellPower)%%%%%%%%%%%
%disp('MPP (W/m2) =')
%disp(maxPowerPoint)

%
% Solar cell efficiency.
%
solarCellEff     = maxPowerPoint/solarPowerAM15;
%solarCellEffNorm = solarCellEff/(maxPowerPointAtAmbTemp/solarPower);

%% Energy balance.

% Creating some arrays to perform operations.
solarPowerTempArray = ones(1,length(emitTemp))*solarPower;
atmPowerTempArray   = ones(1,length(emitTemp))*atmPower;

% =========================================================================
% Energy balances.
% =========================================================================

% Running a test/validation case.
if isequal(runTest, 'yes')
   
    % This calculates Fig. 2 in Perrakis et al., 2020 paper.
    coolPowerTempArray = radPowerForTempArray - atmPowerTempArray + convPowerTempArray ...
        - solarPower;
else
    
    coolPowerTempArray = radPowerForTempArray - atmPowerTempArray + convPowerTempArray ...
        - solarPowerTempArray + maxPowerPoint + nonThermalPower;

end

disp('Max. non thermal radiation =')
disp(max(nonThermalPower))

% Solar power AM.
disp('Solar power AM1.5 in W/m2 =')
disp(solarPowerAM15) % ~1000 W/m2 for AM1.5G and 900 W/m2 for AM 1.5D.

% Atmospheric power.
disp('Atmospheric power in W/m2 =')
disp(atmPower)

% Solar power.
disp('Solar power in W/m2 =')
disp(solarPower)


% Emiter temperature for the standard test: T = 298 K, AM1.5G, 1000 W/m2
% irradiance.
%emitTempIndex = find(emitTemp > 298 - 1/2 & emitTemp < 298 + 1/2);
%emitTemp(emitTempIndex)

% =========================================================================
% Temperature coefficient, betaP.
% =========================================================================
betaP = (maxPowerPointAtAmbTemp - maxPowerPointAtEmitTemp)/(tempAmb - emitTemp(emitTempIndex))*...
    (100/maxPowerPointAtAmbTemp);
disp('Temperature coefficient =')
disp(betaP)


%% Average properties.


[averSolarAbs, averSubGapRef, averEmitWind1, averEmitWind2, averEmitBroad, averSolarRef ] = ...
    averagePropsFunc(nLambda, lambdaArray, absSilicon, ref, emitSpectral, ...
    solarPowerPerMicron, emitTempLook );

%% log file.
% Open .log file to store simulation parameters.
fidlog = fopen(strcat(resultsFolderName,'/simulParamPV.log'),'wt');
% Format specification
if isequal(runTest ,'yes')
    formatSpecLog1 = "This simulation is only a test \n";
    fprintf(fidlog,formatSpecLog1);
    
else
    % PV cell thickness.
    formatSpecLog2 = "Si PV cell thickness: %0.3f um \n";
    fprintf(fidlog, formatSpecLog2, thickSi);
    
    % Voltage array limits.
    formatSpecLog3 = "Voltage range: %0.3f -  %0.3f V \n";
    fprintf(fidlog, formatSpecLog3, voltArray(1), voltArray(length(voltArray)));   
 
    % Ambiente temperature.
    formatSpecLog3 = "Ambiente temperature: %0.3f K \n";
    fprintf(fidlog, formatSpecLog3, tempAmb); 
    
    % Convection + conduction coefficient.
    formatSpecLog4 = "Convection coefficient: %0.3f W/m2 K \n";
    fprintf(fidlog, formatSpecLog4, convCoeff); 
    
    % normal calculations of hemispherical.
    if isequal(angleDef, 'normal')
        formatSpecLog5 = "normal calculations \n";
    elseif isequal(angleDef, 'hemisph')
        formatSpecLog5 = "hemispherical calculations \n";
        fprintf(fidlog, formatSpecLog5);
    end
    
    % Wavelength window.
    formatSpecLog6 = "Wavelength range: %0.3f -  %0.3f um \n";
    fprintf(fidlog, formatSpecLog6, lambdaInitial, lambdaFinal);   
 
    % Solar power absorbed by the structure.
    formatSpecLog7 = "Solar power aborbed by the structure %0.3f W/m \n";
    fprintf(fidlog, formatSpecLog7, solarPower);    
    
    % Solar power AM1.5G in W/m2.
    formatSpecLog8 = "Solar power AM1.5G %0.3f W/m2 \n";
    fprintf(fidlog, formatSpecLog8, solarPowerAM15); 
    
    % Short circuit current in A/m2.
    formatSpecLog9 = "Short circuit current: %0.3f A/m2 \n";
    fprintf(fidlog, formatSpecLog9, shortCircCurrent);    
    
    % Series and shunt resistances.
    formatSpecLog10 = "Rs =  %0.7f Ohm m2 and Rsh =  %0.3f Ohm m2 \n";
    fprintf(fidlog, formatSpecLog10, seriesRes, shuntRes);    
    
    % MPP at ambient temperature.
    formatSpecLog11 = "MPP at ambient temperature:  %0.3f W/m2 \n";
    fprintf(fidlog, formatSpecLog11, maxPowerPointAtAmbTemp);     
    
    % MPP at emiters temperature.
    formatSpecLog12 = "MPP at emiter temperature:  %0.3f W/m2 \n";
    fprintf(fidlog, formatSpecLog12, maxPowerPointAtEmitTemp);
    
    % FF at ambient temperature.
    formatSpecLog13 = "FF at ambient temperature:  %0.3f \n";
    fprintf(fidlog, formatSpecLog13, ambTempFF);     
    
    % FF at emitter temperature.
    formatSpecLog14 = "FF at ambient temperature:  %0.3f \n";
    fprintf(fidlog, formatSpecLog14, emitTempFF);      
    
     % Atmospheric power.
    formatSpecLog15 = "Atmospheric power:  %0.3f W/m2 \n";
    fprintf(fidlog, formatSpecLog15, atmPower);    
       
    % Temperature coefficient.
    formatSpecLog16 = "Temperature coefficient:  %0.3f perc/K \n";
    fprintf(fidlog, formatSpecLog16, betaP);   
    
    % Equilibrium temperature.
    formatSpecLog17 = "Equilibrium temperature (remember that's two step process):  %0.3f K \n";
    fprintf(fidlog, formatSpecLog17, emitTempLook);
    
    % MPP voltage.
    formatSpecLog18 = "MPP voltage (remember that's two step process):  %0.3f V \n";
    fprintf(fidlog, formatSpecLog18, Vmpp);        
    
    % Solar cell efficiency.
    formatSpecLog19 = "Solar cell efficiency:  %0.3f \n";
    fprintf(fidlog, formatSpecLog19, solarCellEff(emitTempIndex));     
    
    % Radiated power by the cooler.
    formatSpecLog20 = "Radiated power by the cooler (W/m2):  %0.3f \n";
    fprintf(fidlog, formatSpecLog20, radPowerForTempArray(emitTempIndex));     
 
    formatSpecLog21 = "Aver. props. in perc. (A [0.3,1.1]; R[1.1,4.0]; E[4,30]; R [0.3,1.1] ): %0.4f %0.4f %0.4f %0.4f \n";
    fprintf(fidlog, formatSpecLog21, averSolarAbs, averSubGapRef, averEmitBroad, averSolarRef);
           
    % Code version.
    formatSpecLog22 = "Code version:  %0.2f \n";
    fprintf(fidlog, formatSpecLog22, 11);      
    
end


%% Ouput data.

% get some data into a file.

% Optical properties.
fidOptProps = fopen(strcat(resultsFolderName,'/opticalProps-PVcode.txt'),'wt');
fprintf(fidOptProps,'%6.6f   %6.6f   %6.6f   %6.6f   %6.6f   %6.6f    %6.6f\n',...
    [lambdaArray; emitSpectral; emissNorm; ref; refNorm; absSilicon; absSiliconNorm]);  % The format string is applied to each element of a
fclose(fidOptProps);

% I-V curve.
fidIV = fopen(strcat(resultsFolderName,'/IV-PVcode.txt'),'wt');
fprintf(fidIV,'%6.6f    %6.6f\n',...
    [voltArray; -currentDens(emitTempIndex,:)]);  % The format string is applied to each element of a
fclose(fidIV);


% Power curve. 
fidPower = fopen(strcat(resultsFolderName,'/Power-PVcode.txt'),'wt');
fprintf(fidPower,'%6.6f    %6.6f    %6.6f\n',...
    [voltArray; cellPower(:,emitTempIndex)'; cellPower(:,ambTempIndex)']);  % The format string is applied to each element of a
fclose(fidPower);



%% Plots.
indexPlot = 1; % Index for numbering figures.

%
% Cooler Emittance.
%

figure(indexPlot); indexPlot = indexPlot + 1;
plot(lambdaArray, emitSpectral, 'Color',[0.35 0.35 0.35], 'LineWidth',1.5)
hold on
area(lam_atm_1,tran_atm_1,'LineWidth',1,'EdgeColor',[0.1 0.7 1.0],...
    'FaceColor',[0.1 0.7 1.0],'FaceAlpha',.05,'EdgeAlpha',.1);
hold on
area(lambdaSolarIrradiance ,solarIrradiance/max(solarIrradiance),'LineWidth',1,'EdgeColor',[1 0.6 0.1],...
    'FaceColor',[1 0.6 0.1],'FaceAlpha',.1,'EdgeAlpha',.2);
hold off
legend('')
legend boxoff
title('Cooler emissivity vs. wavelength')
xlabel('Wavelength, \lambda (\mum)')
ylabel('Emissivity')
ylim([0.0 1.0])
xlim([0.3 30])
set(gca, 'XScale', 'log')
xticks([0.3, 1.1, 4, 8, 13, 30]);
xticklabels({'0.3', '1.1', '4', '8', '13','30' });
%run 'settings/setGcaForPlots.m'

%
% Plots of power.
%
figure(indexPlot); indexPlot = indexPlot + 1;
plot(emitTemp, radPowerForTempArray,'LineWidth', 1.5)
hold on
plot(emitTemp, atmPowerTempArray,'LineWidth', 1.5)
hold on
plot(emitTemp(1:2:length(emitTemp)), coolPowerTempArray(1:2:length(emitTemp)),'-s', 'MarkerFaceColor', 'white','MarkerSize',7, 'LineWidth', 1.5)
hold on
plot(emitTemp, convPowerTempArray,'LineWidth', 1.5)
hold on
plot(emitTemp, maxPowerPoint,'LineWidth', 1.5)
hold on
plot(emitTemp, nonThermalPower,'LineWidth', 1.5)
hold off
yline(0.0);
title('Each term of the energy balance vs. cooler temperature')
legend('P_{rad}', 'P_{atm}', 'P_{cool} (equil.)','P_{conv}','P_{mpp}','P_{nonthermrad}', '','Location', 'SouthEast')
legend boxoff
xlabel('Emitter temperature (K)')
ylabel('Power (W/m^2)')
set(gca,'fontsize',17)
set(gca,'linewidth',1)
set(gcf,'color','w') %to get white background
text(300,600, ['Cooler Temp. = ', num2str(round(emitTempLook,2)), ' K'], 'FontSize', 16, 'FontName', 'calibri' )
text(300,680, ['Amb. Temp.   = ', num2str(round(tempAmb,2)), ' K'], 'FontSize', 16, 'FontName', 'calibri' )
text(300,770, ['Rad. Power    = ', num2str(round(radPowerForTempArray(emitTempIndex),0)), ' W/m^2'], 'FontSize', 16, 'FontName', 'calibri' )
%run 'settings/setGcaForPlots.m'
%ylim([0.0 1.0])
xlim([min(emitTemp) max(emitTemp)])


%
% Current density and cell output power versus voltage.
%

figure(indexPlot); indexPlot = indexPlot + 1;
%yyaxis left
plot(voltArray, -currentDens(emitTempIndex,:)', 'LineWidth', 1.5)
ylabel('Current density (A/m^2)')
%hold on
%yyaxis right
%plot(voltArray, cellPower(:,emitTempIndex)','--', 'LineWidth', 1.5)
text(0.56,200, ['Short-circuit current = ', num2str(round(shortCircCurrent,1)),' A/m^2'], 'FontSize', 18, 'FontName', 'calibri' )
text(0.56,175, ['Fill factor = ', num2str(round(emitTempFF,2)),], 'FontSize', 18, 'FontName', 'calibri' )
%text(2,8,'A Simple Plot','Color','red','FontSize',14)

%hold off
title('Current-voltage characteristics')
legend('')
legend boxoff
xlabel('Voltage (V)')
xlim([0.55 openCircuitVoltAtEmitTemp])
xticks([0.55 0.6 0.65 openCircuitVoltAtEmitTemp]);
strVoc = num2str(round(openCircuitVoltAtEmitTemp,3));
markerVoc = cat(2,'V_{oc} = ',strVoc);
xticklabels({'0.55', '0.6', '0.65', markerVoc });
%run 'settings/setGcaForPlots.m'


%
% Power versus voltage for ambient temperature and real emitter's temperature
%
figure(indexPlot); indexPlot = indexPlot + 1;
plot(voltArray, cellPower(:,emitTempIndex),'-s', 'MarkerFaceColor', 'white','MarkerSize',7, 'linewidth', 1.5)
hold on
plot(voltArray, cellPower(:,ambTempIndex),'linewidth', 1.5)
hold off
%run 'settings/setGcaForPlots.m'
title('Output power at cooler and emitter temperature')

legend(['Emitter temperature,   P_{mpp} = ', num2str(round(maxPowerPointAtEmitTemp,2)),' W/m^2'],...
       ['Ambient temperature, P_{mpp} = ', num2str(round(maxPowerPointAtAmbTemp,1)), ' W/m^2'])

legend boxoff
ylabel('Output power (W/m^{2})','FontName','calibri','FontWeight','normal','Color','black')
xlabel('Applied voltage (V)','FontName','calibri','FontWeight','normal','Color','black')
ylim([0 300]);
xlabel('Voltage (V)')
xlim([0.3 openCircuitVoltAtAmbTemp])
xticks([0.3 0.4 0.5 0.6  openCircuitVoltAtAmbTemp]);
strVocAmb = num2str(round(openCircuitVoltAtAmbTemp,3));
markerVocAmb = cat(2,'V_{oc}^{amb} = ',strVocAmb);
xticklabels({'0.3', '0.4', '0.5', '0.6', markerVocAmb});
xtickangle(0)


%
% Fitting to know the temperature coefficient.
%

p = polyfit(emitTemp,solarCellEff*100,1);
%tempCoeff = p(1)
%
% Normalized solar cell efficiency vs emitter temperature.
%
figure(indexPlot); indexPlot = indexPlot + 1;
plot(emitTemp(1:2:length(emitTemp)), solarCellEff(1:2:length(emitTemp))*100, 's', 'MarkerFaceColor', 'white','MarkerSize',7,'LineWidth', 2)
hold on
plot(emitTemp, p(2) + emitTemp*p(1), 'LineWidth', 1.5)
hold off
title('Solar cell efficiency vs. emitter temperature')
legend(['Efficiency (%)'], ['linear fitting / Temp. Coeff. =', num2str(round(betaP,2))])
legend boxoff
xlabel('Emitter temperature (K)')
ylabel('Efficiency')
set(gca,'fontsize',17)
set(gca,'linewidth',1)
set(gcf,'color','w') %to get white background
%run 'settings/setGcaForPlots.m'
%ylim([0.0 1.0])
xlim([min(emitTemp) max(emitTemp)])

% --------------------------
% Plots for testing results.
% --------------------------
if isequal(runTest,'yes')
    %
    % Atmospheric transmittance and solar spectrum.
    %
    figure(indexPlot); indexPlot = indexPlot + 1;
    % Left axis.
    yyaxis left
    area(lambdaSolarIrradiance ,solarIrradiance,'LineWidth',1,...
        'EdgeColor',[1 0.6 0.1],'FaceColor',[1 0.6 0.1],'FaceAlpha',.1,'EdgeAlpha',.9);
    ylabel('Solar irrandiance (W/m^2\mum)','FontName','calibri',...
        'FontWeight','normal','Color','black')
    % Right axis.
    yyaxis right
    plot(lambdaArray,emitIdealRadCool,'--','Color', color_scheme_aaas(2,:),'LineWidth',2)
    hold on
    area(lambdaArray, atmTransInterp,'LineWidth',1,'EdgeColor',[0.1 0.7 1.0],...
        'FaceColor',[0.1 0.7 1.0],'FaceAlpha',.1,'EdgeAlpha',.9);
    hold off
    ylabel('Transmittance','FontName','calibri','FontWeight','normal','Color','black')
    ax = gca;
    ax.YAxis(1).Color = [1.0 0.6 0.1];
    ax.YAxis(2).Color = [0.1 0.7 1.0];
    legend('Solar spectrum', 'ideal selective cooler', 'Atmosph. transmittance')
    xlabel('Wavelength, \lambda (\mum)')
    set(gca,'fontsize',17)
    set(gca,'linewidth',1)
    set(gcf,'color','w') % To get white background.
    title('Solar Spectrum and Atmospheric Transmittance','FontName',...
        'calibri','FontWeight','normal','Color','black')
    run 'settings/setGcaForPlots.m'
    xlabel('Wavelength (\mum)','FontName','calibri','FontWeight','normal','Color','black')
    legend boxoff
    %ylim([0 1]);
    xlim([0 20])
    xticks([0.30 2.5 5.0 8.0 13 15 20]);
    xticklabels({'0.30','2.5','5.0','8.0','13','15', '20'});
    
    
    % Data for validation.
    % Source: Passive radaitve cooling and other photonic approaches for the
    % temperature control of PVs by Perrakis. Fig. 2
    %toValidate = dlmread('perrakis-h0.dat');
    toValidate = dlmread('literatureData/perrakis-h0.dat');
    xValidation = toValidate(:,1); % read x coordinate
    yValidation = toValidate(:,2); % read y coordinate   
    
    figure(indexPlot); indexPlot = indexPlot + 1;
    plot(emitTemp, coolPowerTempArray, xValidation, yValidation, 'o--', 'LineWidth', 2)
    yline(0.0);
    legend('This code', 'Perrakis et al.','')
    legend boxoff
    xlabel('Temperature (K)')
    ylabel('Cooling power, (W/m^2)')
    set(gca,'fontsize',17)
    set(gca,'linewidth',1)
    set(gcf,'color','w') %to get white background
    run 'settings/setGcaForPlots.m'
    %yticks([-50 -40 -30 -20 -15 -12.5 -10 -7.5 -5 -2.5 0 2.5 5 7.5 10 12.5 15 20 30 40 50])
    %ylim([0.0 1.0])
    xlim([300 360])
    
end

% --------------------------
% Plots for testing results.
% --------------------------
if isequal(runTest2,'yes')
    %
    % Current density versus voltage.
    %
    % Data for validation.
    % Source: Passive radaitve cooling and other photonic approaches for the
    % temperature control of PVs by Perrakis et al. OPEX, 2020. Fig. 2
    
    toValidateIV = dlmread('literatureData/currentVoltageGreenOPEXPaper.txt');
    %toValidate = dlmread('perrakis-h18.txt');
    xValidationIV = toValidateIV(:,1); % read x coordinate
    yValidationIV = toValidateIV(:,2); % read y coordinate
    
    toValidatePV = dlmread('literatureData/powerVoltagePerrakis.txt');
    %toValidate = dlmread('perrakis-h18.txt');
    xValidationPV = toValidatePV(:,1); % read x coordinate
    yValidationPV = toValidatePV(:,2); % read y coordinate
    
    
    figure(indexPlot); indexPlot = indexPlot + 1;
    yyaxis left
    plot(voltArray, -currentDens(emitTempIndex,:)',xValidationIV, yValidationIV, 'r-o', 'LineWidth', 2)
    ylabel('Current density (A/m^2)')
    hold on
    yyaxis right
    plot(voltArray, cellPower(:,emitTempIndex)','--',xValidationPV, yValidationPV, 'g-o', 'LineWidth', 2)
    ylabel('Cell output power (W/m^2)')
    hold off
    legend('Current density','Perrakis paper', 'Cell output power','Perrakis paper', 'Location', 'SouthWest')
    legend boxoff
    xlabel('Voltage, (V)')
    set(gca,'fontsize',17)
    set(gca,'linewidth',1)
    set(gcf,'color','w') %to get white background
    %run 'settings/setGcaForPlots.m'
    xlim([0.55 0.7])
    xticks([min(voltArray) 0.2 0.3 0.4 0.5 0.6 openCircuitVoltAtEmitTemp]);
    
    
    %
    % Recombination current
    %
    % Data for validation.
    % Source: Passive radaitve cooling and other photonic approaches for the
    % temperature control of PVs by Perrakis et al. OPEX, 2020. Fig. 5a
    toValidateAuger = dlmread('literatureData/augerGreen.txt');
    %toValidate = dlmread('perrakis-h18.txt');
    xValidationAuger = toValidateAuger(:,1); % read x coordinate
    yValidationAuger = toValidateAuger(:,2); % read y coordinate
    figure(indexPlot); indexPlot = indexPlot + 1;
    plot(voltArray, augerCurrentDens(emitTempIndex,:), voltArray, currentSat(emitTempIndex)*...
        (exp(ECHARGE*voltArray./(KBOLTZ*emitTemp(emitTempIndex))) - 1),...
        xValidationAuger,yValidationAuger,'r-o', 'LineWidth', 2)
    legend('Auger recombination', 'Saturation current recombination', 'Perrakis')
    legend boxoff
    xlabel('Voltage (V)')
    ylabel('Recombination current (A/m^{2})')
    set(gca,'fontsize',17)
    set(gca,'linewidth',1)
    set(gcf,'color','w') %to get white background
   % run 'settings/setGcaForPlots.m'
    %ylim([0.0 1.0])
    xlim([0.6 openCircuitVoltAtEmitTemp])
        
    
end


% Comparison between Si normal and hemispherical absoprtion
figure(indexPlot); indexPlot = indexPlot + 1;
plot(xAbsPV, absSilicon, '-s', 'MarkerFaceColor', 'white','MarkerSize',7, 'LineWidth', 1.5)
hold on
plot(xAbsPV, absSiliconNorm, 'LineWidth', 1.5)
hold off
%run 'settings/setGcaForPlots.m'
xlabel('Wavelentgh (\mum)')
ylabel('Silicon absorptivity')
title('Comparison between Si normal and hemispherical absoprtion')
legend boxoff
legend('Hemisph.', 'Normal')
xlim([0.3, 2])


%% ===================== Comparison exports =====================
% Energy-balance terms vs emitter temperature (7 columns).
ebFid = fopen(fullfile(resultsFolderName,'energyBalanceTerms.txt'),'wt');
fprintf(ebFid, '%g %g %g %g %g %g %g\n', ...
    [emitTemp; radPowerForTempArray; atmPowerTempArray; convPowerTempArray; ...
     coolPowerTempArray; maxPowerPoint; nonThermalPower]);
fclose(ebFid);

% Scalar results.
scFid = fopen(fullfile(resultsFolderName,'scalars.txt'),'wt');
fprintf(scFid, 'isc_A_m2 %.10g\n', shortCircCurrent);
fprintf(scFid, 'voc_equil_V %.10g\n', openCircuitVoltAtEmitTemp);
fprintf(scFid, 'voc_amb_V %.10g\n', openCircuitVoltAtAmbTemp);
fprintf(scFid, 'ff_equil %.10g\n', emitTempFF);
fprintf(scFid, 'ff_amb %.10g\n', ambTempFF);
fprintf(scFid, 'mpp_equil_W_m2 %.10g\n', maxPowerPointAtEmitTemp);
fprintf(scFid, 'mpp_amb_W_m2 %.10g\n', maxPowerPointAtAmbTemp);
fprintf(scFid, 'atm_power_W_m2 %.10g\n', atmPower);
fprintf(scFid, 'solar_power_abs_W_m2 %.10g\n', solarPower);
fprintf(scFid, 'solar_power_am15_W_m2 %.10g\n', solarPowerAM15);
fprintf(scFid, 'beta_p_perc_K %.10g\n', betaP);
fprintf(scFid, 'efficiency_equil %.10g\n', solarCellEff(emitTempIndex));
fprintf(scFid, 'equil_temp_K %.10g\n', emitTempLook);
fprintf(scFid, 'vmpp_V %.10g\n', Vmpp);
fclose(scFid);

% Save all open figures as PNG.
figs = findall(0,'Type','figure');
for kfig = 1:numel(figs)
    try
        print(figs(kfig), fullfile(resultsFolderName, ...
            sprintf('matlab_fig%02d.png', kfig)), '-dpng', '-r120');
    catch
    end
end

disp('Comparison exports written.');



